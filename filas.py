import heapq
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from randomizer import LCG
from yaml_parser import SimpleYAMLParser

@dataclass(order=True)
class Evento:
    tempo: float
    tipo: str = field(compare=False)      
    fila_id: str = field(compare=False)
    servidor: int = field(compare=False, default=None)
    cliente_id: int = field(compare=False, default=None)
    externa: bool = field(compare=False, default=False)

class Fila:
    def __init__(self, id_fila: str, config: dict):
        self.id = id_fila
        self.c = config.get('servers', 1)
        self.K = config.get('capacity', float('inf'))
        self.service_min = config.get('service_min', 1.0)
        self.service_max = config.get('service_max', 2.0)
        
        self.num_clientes = 0
        self.servidores = [0] * self.c
        self.perdas = 0
        self.tempo_estado = {}
        
        self.destinos = config.get('routing', {})
        
    def acumula_tempo(self, delta: float):
        """Acumula tempo no estado atual"""
        estado = self.num_clientes
        self.tempo_estado[estado] = self.tempo_estado.get(estado, 0.0) + delta
        
    def pode_aceitar_cliente(self) -> bool:
        """Verifica se a fila pode aceitar mais um cliente"""
        return self.num_clientes < self.K
        
    def tem_servidor_livre(self) -> bool:
        """Verifica se há servidor livre"""
        return any(s == 0 for s in self.servidores)
        
    def ocupar_servidor(self) -> int:
        """Ocupa um servidor livre e retorna seu índice"""
        for i in range(self.c):
            if self.servidores[i] == 0:
                self.servidores[i] = 1
                return i
        return -1
        
    def liberar_servidor(self, servidor_id: int):
        """Libera um servidor"""
        if 0 <= servidor_id < self.c:
            self.servidores[servidor_id] = 0

class RedeFilas:
    def __init__(self, config_file: str):
        self.filas = {}
        self.chegadas_externas = {}
        self.general = {}
        self.rng = None
        self.num_random_limit = None
        self.carregar_configuracao(config_file)
        
    def carregar_configuracao(self, config_file: str):
        """Carrega configuração do arquivo YAML"""
        parser = SimpleYAMLParser()
        config = parser.load(config_file)
            
        geral = config.get('general', {})
        self.general = geral if isinstance(geral, dict) else {}
        seed = geral.get('seed', 42)
        self.rng = LCG(seed=seed)
        
        filas_config = config.get('queues', {})
        for fila_id, fila_config in filas_config.items():
            self.filas[fila_id] = Fila(fila_id, fila_config)

        self.chegadas_externas = config.get('arrivals', {})

        self._validar_configuracao()
            
    def _validar_configuracao(self):
        """Valida coerência básica da configuração carregada."""
        if not self.filas:
            raise ValueError("Nenhuma fila definida em 'queues'.")

        for fila_id, fila in self.filas.items():
            if not isinstance(fila.c, int) or fila.c <= 0:
                raise ValueError(f"'servers' inválido para a fila '{fila_id}': {fila.c!r}")

            if fila.K != float('inf'):
                if not isinstance(fila.K, int) or fila.K <= 0:
                    raise ValueError(f"'capacity' inválida para a fila '{fila_id}': {fila.K!r}")

            if fila.service_min is None or fila.service_max is None:
                raise ValueError(f"'service_min'/'service_max' ausentes para a fila '{fila_id}'.")
            if float(fila.service_min) > float(fila.service_max):
                raise ValueError(
                    f"'service_min' > 'service_max' para a fila '{fila_id}': {fila.service_min} > {fila.service_max}"
                )

        if self.chegadas_externas and not isinstance(self.chegadas_externas, dict):
            raise ValueError("Seção 'arrivals' deve ser um dicionário.")

        for fila_id, chegada_cfg in (self.chegadas_externas or {}).items():
            if fila_id not in self.filas:
                raise ValueError(f"Chegada externa definida para '{fila_id}', mas essa fila não existe em 'queues'.")
            if not isinstance(chegada_cfg, dict):
                raise ValueError(f"Config de chegada externa para '{fila_id}' deve ser um dicionário.")
            if 'min' in chegada_cfg and 'max' in chegada_cfg:
                if float(chegada_cfg['min']) > float(chegada_cfg['max']):
                    raise ValueError(
                        f"'min' > 'max' em 'arrivals.{fila_id}': {chegada_cfg['min']} > {chegada_cfg['max']}"
                    )

        self._validar_roteamento()

    def _validar_roteamento(self):
        """Valida que as probabilidades de roteamento somam 1 (quando definidas)."""
        eps = 1e-9
        for fila_id, fila in self.filas.items():
            if not fila.destinos:
                continue
            if not isinstance(fila.destinos, dict):
                raise ValueError(f"Seção 'routing' da fila '{fila_id}' deve ser um dicionário.")
            soma = 0.0
            for destino, prob in fila.destinos.items():
                if destino != 'exit' and destino not in self.filas:
                    raise ValueError(
                        f"Destino '{destino}' no roteamento da fila '{fila_id}' não existe em 'queues'."
                    )
                try:
                    prob_f = float(prob)
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Probabilidade inválida no roteamento de '{fila_id}' para '{destino}': {prob!r}"
                    )
                if prob_f < 0:
                    raise ValueError(
                        f"Probabilidade negativa no roteamento de '{fila_id}' para '{destino}': {prob_f}"
                    )
                soma += prob_f

            if abs(soma - 1.0) > eps:
                raise ValueError(
                    f"Roteamento da fila '{fila_id}' deve somar 1.0, mas somou {soma:.6f}. "
                    "Ajuste o YAML para incluir todos os destinos (incluindo 'exit' se aplicável)."
                )
        
    def simular(self, num_random: int = 100000, tempo_primeira_chegada: float = 2.0):
        """Executa a simulação da rede de filas"""
        eventos = []
        tempo_atual = 0.0
        ultimo_tempo = 0.0
        cliente_id = 0

        self.num_random_limit = num_random
        
        def agendar(evento):
            heapq.heappush(eventos, evento)
            
        for fila_id, config_chegada in self.chegadas_externas.items():
            if config_chegada.get('enabled', True):
                inicio = config_chegada.get('start', tempo_primeira_chegada)
                agendar(Evento(
                    tempo=float(inicio),
                    tipo="chegada",
                    fila_id=fila_id,
                    cliente_id=cliente_id,
                    externa=True,
                ))
                cliente_id += 1
                
        while eventos and self.rng.count < num_random:
            evento = heapq.heappop(eventos)
            tempo_atual = evento.tempo
            delta = tempo_atual - ultimo_tempo
            
            for fila in self.filas.values():
                fila.acumula_tempo(delta)
                
            ultimo_tempo = tempo_atual
            
            if evento.tipo == "chegada":
                self._processar_chegada(evento, eventos, tempo_atual, cliente_id)
                if evento.externa:
                    cliente_id += 1
                    
            elif evento.tipo == "saida":
                cliente_id = self._processar_saida(evento, eventos, tempo_atual, cliente_id)
                
            if self.rng.count >= num_random:
                break
                
        return self._gerar_relatorio(ultimo_tempo)
        
    def _processar_chegada(self, evento, eventos, tempo_atual, cliente_id):
        """Processa evento de chegada"""
        fila = self.filas[evento.fila_id]
        
        if evento.externa and evento.fila_id in self.chegadas_externas:
            config_chegada = self.chegadas_externas[evento.fila_id]
            if self.num_random_limit is None or self.rng.count < self.num_random_limit:
                inter_min = config_chegada.get('min', 1.0)
                inter_max = config_chegada.get('max', 4.0)
                intervalo = inter_min + (inter_max - inter_min) * self.rng.next()
                
                heapq.heappush(eventos, Evento(
                    tempo=tempo_atual + intervalo,
                    tipo="chegada",
                    fila_id=evento.fila_id,
                    cliente_id=cliente_id,
                    externa=True,
                ))
        
        if fila.pode_aceitar_cliente():
            fila.num_clientes += 1
            
            if fila.tem_servidor_livre():
                servidor_id = fila.ocupar_servidor()
                if self.num_random_limit is None or self.rng.count < self.num_random_limit:
                    tempo_servico = (fila.service_min + 
                                   (fila.service_max - fila.service_min) * self.rng.next())
                    
                    heapq.heappush(eventos, Evento(
                        tempo=tempo_atual + tempo_servico,
                        tipo="saida",
                        fila_id=fila.id,
                        servidor=servidor_id,
                        cliente_id=evento.cliente_id
                    ))
        else:
            fila.perdas += 1
            
    def _processar_saida(self, evento, eventos, tempo_atual, cliente_id):
        """Processa evento de saída"""
        fila = self.filas[evento.fila_id]
        fila.num_clientes -= 1
        fila.liberar_servidor(evento.servidor)
        
        if fila.num_clientes >= fila.c:
            servidor_id = fila.ocupar_servidor()
            if self.num_random_limit is None or self.rng.count < self.num_random_limit:
                tempo_servico = (fila.service_min + 
                               (fila.service_max - fila.service_min) * self.rng.next())
                
                heapq.heappush(eventos, Evento(
                    tempo=tempo_atual + tempo_servico,
                    tipo="saida",
                    fila_id=fila.id,
                    servidor=servidor_id,
                    cliente_id=evento.cliente_id
                ))
        
        if fila.destinos:
            if self.num_random_limit is None or self.rng.count < self.num_random_limit:
                rand_val = self.rng.next()
                prob_acum = 0.0
                
                for destino, probabilidade in fila.destinos.items():
                    prob_acum += probabilidade
                    if rand_val <= prob_acum:
                        if destino != "exit":
                            heapq.heappush(eventos, Evento(
                                tempo=tempo_atual,
                                tipo="chegada",
                                fila_id=destino,
                                cliente_id=evento.cliente_id,
                                externa=False,
                            ))
                        break
                        
        return cliente_id
        
    def _gerar_relatorio(self, tempo_total):
        """Gera relatório final da simulação"""
        resultado = {
            "tempo_global": tempo_total,
            "numeros_aleatorios_usados": self.rng.count,
            "filas": {}
        }
        
        for fila_id, fila in self.filas.items():
            distribuicao = {}
            for estado, tempo in fila.tempo_estado.items():
                distribuicao[estado] = tempo / tempo_total if tempo_total > 0 else 0.0
                
            resultado["filas"][fila_id] = {
                "perdas": fila.perdas,
                "tempo_estado": fila.tempo_estado,
                "distribuicao": distribuicao
            }
            
        return resultado
