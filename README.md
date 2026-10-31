# TEKO KA’A

**TEKO KA’A** é uma plataforma de monitoramento inteligente da saúde visual de plantas, desenvolvida com foco em visão computacional, análise de imagens em tempo real e acompanhamento de indicadores visuais em ambientes controlados, como estufas, viveiros, laboratórios e projetos de agricultura experimental.

O projeto busca apoiar a identificação precoce de possíveis sinais de estresse visual em plantas, analisando características como coloração, área vegetal, textura, índice de verde e variações visuais ao longo do tempo.

> O objetivo inicial do TEKO KA’A não é substituir uma avaliação agronômica especializada, mas oferecer uma ferramenta de apoio ao monitoramento, capaz de gerar alertas visuais, histórico de acompanhamento e informações úteis para tomada de decisão.

---

## Visão Geral

O TEKO KA’A utiliza técnicas de visão computacional para capturar imagens da planta, processar visualmente o frame em tempo real e apresentar os resultados em um dashboard web interativo.

A aplicação permite visualizar:

- Imagem original da câmera;
- Mapa de segmentação visual da planta;
- Indicadores de saúde visual;
- Métricas de coloração e textura;
- Gráficos em tempo real;
- Relatório automático;
- Histórico de leituras.

---

## Principais Funcionalidades

- Captura de imagem em tempo real;
- Processamento visual com OpenCV e PlantCV;
- Segmentação da região da planta;
- Análise de composição visual por cores;
- Identificação de áreas verdes, amareladas, marrons/secas e escuras;
- Cálculo de métricas como área vegetal, índice ExG e textura;
- Classificação visual da condição da planta;
- Dashboard web interativo;
- Gráficos de acompanhamento;
- Relatório automático com diagnóstico visual;
- Histórico de leituras;
- Estrutura preparada para evolução científica e aplicação como produto.

---

## Tecnologias Utilizadas

### Backend

- Python
- Flask
- OpenCV
- PlantCV
- NumPy

### Frontend

- HTML5
- CSS3
- JavaScript
- Chart.js

### Visão Computacional

- Segmentação por cores
- Análise HSV
- Índice ExG
- Análise de textura
- Processamento de frames em tempo real

---

## Configuração da Câmera

No arquivo `app.py`, altere a variável `CAMERA_SOURCE`.

Para webcam local:

```python
CAMERA_SOURCE = 1
```

Para câmera IP do celular:

```python
CAMERA_SOURCE = "http://192.168.0.25:8080/video"
```

O celular e o computador precisam estar na mesma rede Wi-Fi.

---

## Execução do Projeto

Criar ambiente virtual:

```bash
python -m venv .venv
```

Ativar ambiente virtual:

```bash
.\.venv\Scripts\Activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Execute:

```bash
python app.py
```

Acesse:

```text
http://localhost:5000
```

---

## Roadmap

### Fase 1 — MVP Visual Confiável

- Integrar PlantCV ao fluxo principal;
- Melhorar segmentação da planta;
- Diferenciar verde, amarelo, marrom e escuro;
- Criar estados claros de análise;
- Centralizar status e índice visual no backend.

### Fase 2 — Histórico e Persistência

- Substituir histórico em localStorage por banco SQLite;
- Registrar leituras com timestamp;
- Salvar métricas por planta ou experimento;
- Permitir análise longitudinal.

### Fase 3 — Responsividade e Acesso Mobile

- Adaptar dashboard para tablets e celulares;
- Permitir acesso ao sistema pela rede local;
- Preparar uso da câmera do próprio dispositivo via navegador.

### Fase 4 — Raspberry Pi como Servidor Local

- Executar o sistema em uma Raspberry Pi 4;
- Utilizar a Raspberry como servidor de processamento;
- Permitir acesso via celular/tablet;
- Processar frames enviados pelo dispositivo do usuário.

### Fase 5 — Produto e Pesquisa

- Criar cadastro de plantas;
- Criar identificação por QR Code;
- Integrar sensores de solo e ambiente;
- Validar métricas com especialistas;
- Criar dataset próprio;
- Evoluir para modelos de detecção com aprendizado de máquina.

---

## Limitações Atuais

A versão atual ainda está em fase experimental:

- A classificação é baseada em regras heurísticas;
- Os limites visuais ainda precisam ser calibrados;
- A análise pode ser afetada por iluminação, sombra e enquadramento;
- Ainda não há validação agronômica formal;
- O sistema ainda não identifica doenças específicas.

---

## Autor

Desenvolvido por **Ulric Rondon**.

## Histórico no MySQL local

O servidor Python salva a primeira análise válida e, depois, uma leitura válida
quando tiver passado pelo menos uma hora desde a última gravação. O intervalo é
consultado no banco e permanece após reiniciar o servidor. Não é uma média por
hora nem uma contagem de tempo ativo acumulado. Períodos sem análise válida não
são preenchidos artificialmente.

A gravação ocorre em uma thread do servidor, mesmo com o navegador fechado,
enquanto o processo `app.py`, a câmera e o monitoramento estiverem ativos.
Ao reiniciar a aplicação, ative novamente o monitoramento. Execute uma única
instância de `app.py`, pois a câmera e o agendamento pertencem a esse processo.

### Configuração

1. No MySQL Workbench, conecte como `root` e execute `setup_mysql.sql` para criar
   o banco `teko_kaa`, sem remover bancos ou tabelas existentes.
2. Copie `.env.example` para `.env` se o arquivo ainda não existir. Preencha
   `MYSQL_PASSWORD` localmente. Use aspas simples em torno da senha se ela
   contiver espaços ou `#`. Não envie esse arquivo ao Git.
3. Com um Python instalado, crie um ambiente: `python -m venv .venv`.
4. Instale as dependências: `.venv\Scripts\python.exe -m pip install -r requirements.txt`.
5. Valide a conexão e crie a tabela: `.venv\Scripts\python.exe database.py`.
6. Inicie: `.venv\Scripts\python.exe app.py`.

A configuração inicial usa o usuário `root` informado para o ambiente local.
O Workbench serve apenas para administrar o banco; não precisa ficar aberto.
Não é necessário Docker. O serviço MySQL deve estar em execução.
O conector segue a documentação oficial:
https://dev.mysql.com/doc/connector-python/en/connector-python-connectargs.html

### Comportamento e limites

- `GET /historico` consulta os registros do MySQL, do mais recente ao mais antigo.
- `DELETE /historico` exclui o histórico após confirmação na interface.
  Se o monitoramento continuar ativo, uma nova análise válida poderá ser salva
  no próximo ciclo de até cinco segundos.
- Não há descarte automático após 72 registros. A consulta atual retorna todos;
  para grandes volumes, será necessário adicionar paginação.
- Os registros antigos de `localStorage` continuam no navegador, mas não são
  importados nem exibidos nesta versão. O histórico MySQL começa vazio.
- Os gráficos em tempo real continuam usando as últimas leituras da página;
  esta integração persiste a tabela de histórico, não cada frame da câmera.
- Se a conexão inicial falhar, o servidor não inicia. Se falhar durante a
  execução, a gravação tenta novamente a cada cinco segundos e registra o erro
  no terminal. Não há fila de recuperação das leituras durante a indisponibilidade.

Testes isolados, sem usar o banco real:
`.venv\Scripts\python.exe -m unittest discover -s tests -v`.

Para preparar o banco e validar a integração automaticamente após preencher o
`.env`, execute `.venv\Scripts\python.exe verificar_mysql.py`. Esse comando cria
somente o banco/tabela ausentes e testa gravação, consulta, intervalo e exclusão
em uma tabela temporária, sem inserir dados de teste no histórico definitivo.

## Integração da análise por composição visual

`plantcv_processor.py` recebe BGR uint8, converte para RGB antes de usar os canais
HSV do PlantCV e retorna um mapa BGR colorido. As quatro classes são exclusivas:
verde saudável, amarelo, marrom/seco e escuro/sombra. Os percentuais de composição
usam os pixels classificados da região candidata como denominador; `area_planta`
usa a área total do frame. `area_verde` permanece como alias de `area_planta`.
Sombras entram apenas dentro dos contornos candidatos; um fundo escuro sozinho
não é considerado planta. A segmentação continua sendo uma heurística por cor:
objetos/solo com cores semelhantes podem entrar na região candidata e sombras
abertas na borda podem ficar fora dela. O índice representa composição visual.

O backend é a fonte do status e do índice. O dashboard usa cálculo local somente
quando esses campos não chegam, mostra os percentuais no relatório e não cria
pontos nos gráficos para estados inválidos. ExG usa a escala bruta -510..510;
textura é o desvio padrão dos pixels em cinza, com escala 0..128.

Ao reativar o monitoramento, o servidor aguarda um frame novo. Resultados de uma
sessão anterior são descartados. Apenas SAUDÁVEL, ATENÇÃO e NÃO SAUDÁVEL, com
análise válida e monitoramento ativo, podem ser gravados no MySQL.

Verificação da integração, com PlantCV real e imagens sintéticas (sem câmera):

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
node tests/test_dashboard.cjs
node tests/test_history.cjs
```

Para executar com `python app.py`, ative primeiro o ambiente do projeto:

```powershell
.\.venv\Scripts\Activate.ps1
python app.py
```

Referência da conversão RGB/HSV do PlantCV:
https://docs.plantcv.org/en/v4.0.1/rgb2hsv/
