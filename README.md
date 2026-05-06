# Simulador de Rede de Filas

## Como usar

Executa usando o arquivo padrão `entrada.yml`:

```bash
python main.py
```

Executa informando um YAML diferente:

```bash
python main.py entrada.yml
```

Opcionalmente, sobrescreve parâmetros via linha de comando:

```bash
python main.py entrada.yml --num-random 100000 --first-arrival 2.0
```

Para salvar a saída em arquivo:

```bash
python main.py entrada.yml > saida.txt
```

## O que tem no YAML de entrada

O arquivo de entrada (ex.: `entrada.yml`) tem 3 seções principais.

### `general`
- `seed`: semente do gerador pseudoaleatório
- `num_random`: quantidade de aleatórios usados na simulação (critério de parada)
- `first_arrival`: tempo padrão da primeira chegada externa

### `arrivals`
Define fluxos de chegada externa por fila.

Para cada fila (ex.: `fila1`):
- `enabled`: ativa/desativa o fluxo
- `start` (opcional): tempo da primeira chegada daquela fila (se não existir, usa `general.first_arrival`)
- `min`/`max`: intervalo do tempo entre chegadas (uniforme em `[min, max]`)

### `queues`
Define as filas e suas propriedades.

Para cada fila (ex.: `fila1`, `fila2`):
- `servers`: número de servidores
- `capacity`: capacidade total da fila (use `.inf` para infinito)
- `service_min`/`service_max`: intervalo do tempo de atendimento (uniforme em `[service_min, service_max]`)
- `routing`: dicionário de destinos e probabilidades (deve somar 1.0)
	- use `exit` para saída do sistema
