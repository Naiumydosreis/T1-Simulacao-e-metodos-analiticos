from filas import RedeFilas
import os
import argparse
import re


def _fila_label(fila_id: str) -> str:
    """Gera um rótulo amigável para Pk(estado)."""
    m = re.search(r"(\d+)$", fila_id)
    return m.group(1) if m else fila_id


def _as_int(value, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def main():
    parser = argparse.ArgumentParser(description="Simulador de Rede de Filas")
    parser.add_argument("config", nargs="?", default="entrada.yml", help="Arquivo .yml de entrada")
    parser.add_argument("--num-random", type=int, default=None, help="Limite de aleatórios (padrão: YAML ou 100000)")
    parser.add_argument("--first-arrival", type=float, default=None, help="Tempo da 1ª chegada (padrão: YAML ou 2.0)")
    args = parser.parse_args()

    config_file = args.config
    
    if not os.path.exists(config_file):
        print(f"Erro: não encontrado '{config_file}'")
        print("Uso: python main.py [entrada.yml] [--num-random N] [--first-arrival T]")
        return
    
    print(f"Config: {config_file}")
    print("=" * 60)
    
    try:
        rede = RedeFilas(config_file)

        num_random = _as_int(args.num_random, _as_int(rede.general.get('num_random'), 100000))
        tempo_primeira_chegada = _as_float(args.first_arrival, _as_float(rede.general.get('first_arrival'), 2.0))

        resultado = rede.simular(
            num_random=num_random,
            tempo_primeira_chegada=tempo_primeira_chegada
        )
        
        print(f"\n=== RESULTADOS ===")
        print(f"Tempo global: {resultado['tempo_global']:.2f}")
        print(f"Aleatórios: {resultado['numeros_aleatorios_usados']}")
        print("=" * 60)
        
        for fila_id, dados_fila in resultado['filas'].items():
            print(f"\n=== FILA {fila_id.upper()} ===")
            print(f"Perdas: {dados_fila['perdas']}")
            
            print("\nProbabilidades:")
            distribuicao = dados_fila['distribuicao']
            label = _fila_label(fila_id)
            for estado in sorted(distribuicao.keys()):
                prob = distribuicao[estado]
                print(f"P{label}({estado}) = {prob:.4f}")
            
            print(f"\nTempo por estado:")
            tempo_estado = dados_fila['tempo_estado']
            for estado in sorted(tempo_estado.keys()):
                tempo = tempo_estado[estado]
                print(f"Estado {estado}: {tempo:.2f}")
        
        print("\n" + "=" * 60)
        print("Concluído")
        
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
