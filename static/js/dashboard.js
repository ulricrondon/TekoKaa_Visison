const toggleMonitoramentoBtn = document.getElementById("toggleMonitoramento");
const toggleTextEl = document.getElementById("toggleText");
const statusPlantaEl = document.getElementById("statusPlanta");
const statusPanelEl = document.getElementById("statusPanel");
const statusChipTextEl = document.getElementById("statusChipText");
const pageTitleEl = document.getElementById("pageTitle");
const pageSubtitleEl = document.getElementById("pageSubtitle");
const pageEyebrowEl = document.getElementById("pageEyebrow");
const appShellEl = document.getElementById("appShell");
const sidebarToggleBtn = document.getElementById("sidebarToggle");

const limparHistoricoBtn = document.getElementById("limparHistorico");
const historicoTabelaBody = document.getElementById("historicoTabelaBody");

const MAX_PONTOS = 30;

const historicoSaude = [];
const historicoAreaVerde = [];
const historicoExg = [];
const historicoTextura = [];
const labelsGrafico = [];

let ultimoDiagnostico = "Aguardando início do monitoramento para gerar diagnóstico.";
let ultimosAlertas = [];
let ultimaRecomendacao = "Mantenha iluminação estável e inicie o monitoramento para obter recomendações.";

const paginas = {
    "tab-mapa": {
        titulo: "Mapa de Saúde da Planta",
        subtitulo: "Visualize a saúde vegetal por diferentes camadas de análise.",
        eyebrow: "Camada principal"
    },
    "tab-original": {
        titulo: "Visão Original",
        subtitulo: "Acompanhe a imagem capturada pela câmera antes do processamento.",
        eyebrow: "Entrada visual"
    },
    "tab-segmentacao": {
        titulo: "Segmentação da Vegetação",
        subtitulo: "Acompanhe o percentual da imagem reconhecido como vegetação.",
        eyebrow: "Camada de segmentação"
    },
    "tab-textura": {
        titulo: "Análise de Textura",
        subtitulo: "Acompanhe a irregularidade visual calculada na região segmentada.",
        eyebrow: "Camada de textura"
    },
    "tab-graficos": {
        titulo: "Gráficos e Histórico",
        subtitulo: "Acompanhe a evolução dos indicadores principais ao longo do tempo.",
        eyebrow: "Análise temporal"
    },
    "tab-relatorio": {
        titulo: "Relatório Inteligente",
        subtitulo: "Diagnóstico automático, alertas e recomendações da análise visual.",
        eyebrow: "Apoio à decisão"
    },
    "tab-historico": {
        titulo: "Histórico Geral",
        subtitulo: "Registros consolidados por hora com índice, métricas e status.",
        eyebrow: "Registro temporal"
    }
};

const metricTargets = {
    area: [
        document.getElementById("areaVerde"),
        document.getElementById("areaVerdeSegmentacao"),
        document.getElementById("relatorioArea")
    ],
    exg: [
        document.getElementById("exgAtual"),
        document.getElementById("exgAtualSegmentacao"),
        document.getElementById("resumoExg"),
        document.getElementById("relatorioExg")
    ],
    textura: [
        document.getElementById("texturaAtual"),
        document.getElementById("texturaAtualSegmentacao"),
        document.getElementById("texturaAtualTextura"),
        document.getElementById("resumoTextura"),
        document.getElementById("relatorioTextura")
    ]
};

function formatarNumero(valor, casas = 2) {
    const numero = Number(valor ?? 0);
    return Number.isNaN(numero) ? "0.00" : numero.toFixed(casas);
}

function normalizarValor(valor, min, max) {
    const numero = Number(valor ?? 0);

    if (Number.isNaN(numero)) {
        return 0;
    }

    const normalizado = ((numero - min) / (max - min)) * 100;
    return Math.max(0, Math.min(100, normalizado));
}

function calcularIndiceSaude(areaVerde, exg, textura) {
    const scoreExg = normalizarValor(exg, -510, 510);
    const scoreArea = normalizarValor(areaVerde, 0, 100);

    // Textura muito alta reduz o índice final.
    const scoreTextura = 100 - normalizarValor(textura, 0, 128);

    const indice =
        (scoreExg * 0.45) +
        (scoreArea * 0.35) +
        (scoreTextura * 0.20);

    return Math.max(0, Math.min(100, indice));
}

function statusValido(status) {
    return ["SAUDÁVEL", "ATENÇÃO", "NÃO SAUDÁVEL"].includes(status);
}

function classificarPorIndice(indiceSaude) {
    if (indiceSaude >= 75) return "SAUDÁVEL";
    if (indiceSaude >= 50) return "ATENÇÃO";
    return "NÃO SAUDÁVEL";
}

function resolverLeitura(dados) {
    const numero = (valor) => Number.isFinite(Number(valor)) ? Number(valor) : 0;
    const areaVerde = numero(dados.area_planta ?? dados.area_verde ?? 0);
    const exg = numero(dados.exg);
    const textura = numero(dados.textura);
    const indice = dados.indice_saude_visual;
    const indiceSaude = indice !== null && indice !== undefined && indice !== "" && Number.isFinite(Number(indice))
        ? Number(indice) : calcularIndiceSaude(areaVerde, exg, textura);
    const statusBackend = typeof dados.status === "string" ? dados.status.trim() : "";
    const monitoramentoAtivo = Boolean(dados.monitoramento_ativo);
    const cameraDisponivel = Boolean(dados.camera_disponivel);
    const statusClassificado = statusBackend || (monitoramentoAtivo && cameraDisponivel
        ? classificarPorIndice(indiceSaude) : "AGUARDANDO");
    const analiseValida = monitoramentoAtivo && cameraDisponivel
        && dados.analise_valida !== false && statusValido(statusClassificado);
    return { areaVerde, exg, textura, indiceSaude, statusClassificado,
             monitoramentoAtivo, cameraDisponivel, analiseValida };
}

function atualizarListaElementos(lista, valor) {
    lista.forEach((el) => {
        if (el) {
            el.textContent = valor;
        }
    });
}

function atualizarBarrasMetricas(areaVerde, exg, textura) {
    document.querySelectorAll(".metric-area .metric-bar i").forEach((bar) => {
        bar.style.width = `${normalizarValor(areaVerde, 0, 100)}%`;
    });

    document.querySelectorAll(".metric-exg .metric-bar i").forEach((bar) => {
        bar.style.width = `${normalizarValor(exg, -510, 510)}%`;
    });

    document.querySelectorAll(".metric-texture .metric-bar i").forEach((bar) => {
        bar.style.width = `${normalizarValor(textura, 0, 128)}%`;
    });
}

function obterClasseStatus(statusTexto) {
    const texto = (statusTexto || "").toUpperCase();

    if (texto.includes("CÂMERA") || texto.includes("CAMERA") || texto.includes("AGUARDANDO") || texto === "PLANTA NÃO DETECTADA") {
        return "status-waiting";
    }

    if (texto.includes("NÃO") || texto.includes("NAO") || texto.includes("ERRO")) {
        return "status-bad";
    }

    if (texto.includes("ATEN")) {
        return "status-warning";
    }

    if (texto.includes("SAUD")) {
        return "status-ok";
    }

    return "status-waiting";
}

function aplicarStatus(statusTexto, indiceSaude = null) {
    const statusBase = statusTexto || "AGUARDANDO";

    let statusExibido = statusBase;

    if (indiceSaude !== null && statusValido(statusBase)) {
        statusExibido = `${statusBase} — ${formatarNumero(indiceSaude, 0)}%`;
    }

    statusPlantaEl.textContent = statusExibido;
    statusChipTextEl.textContent = statusExibido;

    statusPanelEl.classList.remove(
        "status-ok",
        "status-warning",
        "status-bad",
        "status-waiting"
    );

    statusPanelEl.classList.add(obterClasseStatus(statusBase));
}

function aplicarEstadoBotao(ativo, cameraDisponivel) {
    toggleMonitoramentoBtn.classList.remove("active", "inactive", "no-camera");

    if (!cameraDisponivel) {
        toggleTextEl.textContent = "Câmera indisponível";
        toggleMonitoramentoBtn.classList.add("no-camera");
        return;
    }

    if (ativo) {
        toggleTextEl.textContent = "Desativar monitoramento";
        toggleMonitoramentoBtn.classList.add("active");
    } else {
        toggleTextEl.textContent = "Ativar monitoramento";
        toggleMonitoramentoBtn.classList.add("inactive");
    }
}

function adicionarPonto(lista, valor) {
    lista.push(Number(valor ?? 0));

    if (lista.length > MAX_PONTOS) {
        lista.shift();
    }
}

function adicionarLabel() {
    const agora = new Date();

    const label = agora.toLocaleTimeString("pt-BR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
    });

    labelsGrafico.push(label);

    if (labelsGrafico.length > MAX_PONTOS) {
        labelsGrafico.shift();
    }

    const resumoHorario = document.getElementById("resumoHorario");
    const relatorioHorario = document.getElementById("relatorioHorario");

    if (resumoHorario) {
        resumoHorario.textContent = label;
    }

    if (relatorioHorario) {
        relatorioHorario.textContent = label;
    }
}

function definirTipoGrafico(label) {
    const texto = label.toLowerCase();

    if (texto.includes("saúde") || texto.includes("saude")) {
        return "saude";
    }

    if (texto.includes("área") || texto.includes("area")) {
        return "area";
    }

    if (texto.includes("textura")) {
        return "textura";
    }

    return "exg";
}

function criarGrafico(canvasId, label, corLinha, corFundo, minY, maxY) {
    const canvas = document.getElementById(canvasId);

    if (!canvas) {
        return null;
    }

    const grafico = new Chart(canvas, {
        type: "line",
        data: {
            labels: labelsGrafico,
            datasets: [{
                label,
                data: [],
                borderColor: corLinha,
                backgroundColor: corFundo,
                fill: true,
                tension: 0.36,
                borderWidth: 2.2,
                pointRadius: 0,
                pointHoverRadius: 4,
                pointBackgroundColor: corLinha
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 220
            },
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        boxWidth: 18,
                        color: "#334155",
                        font: {
                            size: 10,
                            weight: "bold"
                        }
                    }
                },
                tooltip: {
                    enabled: true,
                    backgroundColor: "#0F172A",
                    titleColor: "#FFFFFF",
                    bodyColor: "#E5E7EB",
                    padding: 10,
                    cornerRadius: 10,
                    displayColors: false
                }
            },
            scales: {
                x: {
                    grid: {
                        color: "rgba(148, 163, 184, 0.10)",
                        drawBorder: false
                    },
                    ticks: {
                        color: "#64748B",
                        maxTicksLimit: 5,
                        font: {
                            size: 10
                        }
                    }
                },
                y: {
                    min: minY,
                    max: maxY,
                    grid: {
                        color: "rgba(148, 163, 184, 0.16)",
                        drawBorder: false
                    },
                    ticks: {
                        color: "#64748B",
                        font: {
                            size: 10
                        }
                    }
                }
            }
        }
    });

    grafico.tipoDado = definirTipoGrafico(label);
    return grafico;
}

const graficos = [
    criarGrafico("graficoSaudeGrande", "Índice de Saúde", "#16A34A", "rgba(22, 163, 74, 0.12)", 0, 100),
    criarGrafico("graficoExgGrande", "ExG", "#15803D", "rgba(21, 128, 61, 0.12)", -510, 510),
    criarGrafico("graficoAreaSegmentacao", "Área da Planta (%)", "#65A30D", "rgba(101, 163, 13, 0.12)", 0, 100),
    criarGrafico("graficoTexturaAba", "Textura", "#267581", "rgba(38, 117, 129, 0.10)", 0, 128)
].filter(Boolean);

function atualizarGraficos() {
    graficos.forEach((grafico) => {
        grafico.data.labels = [...labelsGrafico];

        if (grafico.tipoDado === "saude") {
            grafico.data.datasets[0].data = [...historicoSaude];
        } else if (grafico.tipoDado === "area") {
            grafico.data.datasets[0].data = [...historicoAreaVerde];
        } else if (grafico.tipoDado === "textura") {
            grafico.data.datasets[0].data = [...historicoTextura];
        } else {
            grafico.data.datasets[0].data = [...historicoExg];
        }

        grafico.update();
    });
}

function redimensionarGraficos() {
    setTimeout(() => {
        graficos.forEach((grafico) => {
            grafico.resize();
            grafico.update();
        });
    }, 100);
}

function calcularTendencia(valorAtual, historico, unidade = "") {
    if (!historico || historico.length < 2) {
        return {
            texto: "Tendência --",
            classe: "neutral"
        };
    }

    const anterior = historico[historico.length - 2];
    const diferenca = Number(valorAtual) - Number(anterior);

    if (Math.abs(diferenca) < 0.01) {
        return {
            texto: "→ estável",
            classe: "neutral"
        };
    }

    const seta = diferenca > 0 ? "↑" : "↓";
    const classe = diferenca > 0 ? "up" : "down";

    return {
        texto: `${seta} ${diferenca > 0 ? "+" : ""}${formatarNumero(diferenca)}${unidade}`,
        classe
    };
}

function aplicarTendencia(elementoId, tendencia, inverter = false) {
    const el = document.getElementById(elementoId);

    if (!el) {
        return;
    }

    let classe = tendencia.classe;

    // Para textura, subir pode ser ruim. Então invertemos a cor.
    if (inverter) {
        if (classe === "up") {
            classe = "down";
        } else if (classe === "down") {
            classe = "up";
        }
    }

    el.textContent = tendencia.texto;
    el.className = `metric-trend ${classe}`;
}

function resumirComposicao(dados) {
    const campos = [["verde_saudavel", "verde saudável"], ["amarelo", "amarelo"],
                    ["marrom", "marrom/seco"], ["escuro", "escuro/sombra"]];
    if (!campos.every(([campo]) => dados[campo] !== null && dados[campo] !== undefined
            && Number.isFinite(Number(dados[campo])))) return "";
    return "Composição da região candidata: " + campos.map(([campo, nome]) =>
        `${formatarNumero(dados[campo])}% ${nome}`).join(", ") + ".";
}

function atualizarRelatorio(areaVerde, exg, textura, indiceSaude, statusClassificado, dados = {}, analiseValida = false) {
    const relatorioStatus = document.getElementById("relatorioStatus");
    const relatorioDiagnostico = document.getElementById("relatorioDiagnostico");
    const relatorioIndiceSaude = document.getElementById("relatorioIndiceSaude");
    const relatorioRecomendacao = document.getElementById("relatorioRecomendacao");
    const alertasLista = document.getElementById("alertasLista");

    if (!analiseValida) {
        ultimoDiagnostico = "Sem análise válida atual para avaliar a composição da planta.";
        ultimaRecomendacao = dados.monitoramento_ativo
            ? "Verifique o enquadramento, a iluminação e a captura da câmera."
            : "Ative o monitoramento e aguarde uma nova análise válida.";
        ultimosAlertas = [];
    } else {
        ultimoDiagnostico = `Classificação visual: ${statusClassificado}. ${resumirComposicao(dados)}`.trim();
        ultimaRecomendacao = statusClassificado === "SAUDÁVEL"
            ? "Mantenha a iluminação e a câmera estáveis para comparar as próximas leituras."
            : "Observe as regiões amarelas, marrons e sombreadas no mapa e compare novas leituras com iluminação estável.";
        ultimosAlertas = [{ tipo: statusClassificado === "SAUDÁVEL" ? "ok" : "warning",
            texto: statusClassificado === "SAUDÁVEL"
                ? "Composição visual classificada como saudável pelo backend."
                : "A composição visual requer acompanhamento conforme a classificação do backend." }];
    }

    if (relatorioStatus) {
        relatorioStatus.textContent = analiseValida ? `${statusClassificado} — ${formatarNumero(indiceSaude, 0)}%` : statusClassificado;
    }

    if (relatorioDiagnostico) {
        relatorioDiagnostico.textContent = ultimoDiagnostico;
    }

    if (relatorioIndiceSaude) {
        relatorioIndiceSaude.textContent = analiseValida ? `${formatarNumero(indiceSaude, 0)}%` : "--";
    }

    if (relatorioRecomendacao) {
        relatorioRecomendacao.textContent = ultimaRecomendacao;
    }

    if (alertasLista) {
        alertasLista.innerHTML = ultimosAlertas
            .map((alerta) => `<div class="alert-item ${alerta.tipo}">${alerta.texto}</div>`)
            .join("");
    }
}

function classeHistoricoStatus(status) {
    const texto = (status || "").toUpperCase();

    if (texto.includes("SAUDÁVEL") && !texto.includes("NÃO")) {
        return "ok";
    }

    if (texto.includes("ATEN")) {
        return "warning";
    }

    return "bad";
}

let carregandoHistorico = false;

async function renderizarHistoricoTabela() {
    if (!historicoTabelaBody || carregandoHistorico) return;
    carregandoHistorico = true;
    try {
        const resposta = await fetch('/historico', { cache: 'no-store' });
        if (!resposta.ok) throw new Error('Histórico indisponível. Verifique a conexão com o MySQL.');
        const historico = await resposta.json();
        historicoTabelaBody.replaceChildren();
        if (!historico.length) {
            historicoTabelaBody.innerHTML = '<tr><td colspan="6">Nenhuma análise válida salva ainda.</td></tr>';
        }
        for (const item of historico) {
            const linha = document.createElement('tr');
            const valores = [
                new Date(Number(item.timestamp)).toLocaleString('pt-BR'),
                `${formatarNumero(item.indiceSaude, 0)}%`,
                `${formatarNumero(item.areaVerde)}%`,
                formatarNumero(item.exg), formatarNumero(item.textura)
            ];
            for (const valor of valores) {
                const celula = document.createElement('td');
                celula.textContent = valor;
                linha.appendChild(celula);
            }
            const celula = document.createElement('td');
            const status = document.createElement('span');
            status.className = `history-status ${classeHistoricoStatus(item.status)}`;
            status.textContent = item.status;
            celula.appendChild(status);
            linha.appendChild(celula);
            historicoTabelaBody.appendChild(linha);
        }
    } catch (erro) {
        historicoTabelaBody.innerHTML = '<tr><td colspan="6">Histórico indisponível. Verifique a conexão com o MySQL.</td></tr>';
        console.warn(erro);
    } finally {
        carregandoHistorico = false;
    }
}
function ativarAba(tabId) {
    document.querySelectorAll(".nav-item").forEach((botao) => {
        botao.classList.toggle("active", botao.dataset.tab === tabId);
    });

    document.querySelectorAll(".tab-panel").forEach((painel) => {
        painel.classList.toggle("active", painel.id === tabId);
    });

    const dadosPagina = paginas[tabId];

    if (dadosPagina) {
        pageTitleEl.textContent = dadosPagina.titulo;
        pageSubtitleEl.textContent = dadosPagina.subtitulo;
        pageEyebrowEl.textContent = dadosPagina.eyebrow;
    }

    if (tabId === "tab-historico") {
        renderizarHistoricoTabela();
    }

    redimensionarGraficos();
}

document.querySelectorAll(".nav-item").forEach((botao) => {
    botao.addEventListener("click", () => {
        ativarAba(botao.dataset.tab);
    });
});

sidebarToggleBtn.addEventListener("click", () => {
    appShellEl.classList.toggle("menu-open");

    const aberto = appShellEl.classList.contains("menu-open");

    sidebarToggleBtn.title = aberto ? "Fechar menu" : "Abrir menu";

    redimensionarGraficos();
});

if (limparHistoricoBtn) {
    limparHistoricoBtn.addEventListener('click', async () => {
        if (!confirm('Excluir todos os registros do histórico no MySQL? Esta ação não pode ser desfeita.')) return;
        limparHistoricoBtn.disabled = true;
        try {
            const resposta = await fetch('/historico', { method: 'DELETE' });
            if (!resposta.ok) throw new Error('Não foi possível limpar o histórico.');
            await renderizarHistoricoTabela();
        } catch (erro) {
            alert(erro.message);
        } finally {
            limparHistoricoBtn.disabled = false;
        }
    });
}
let requisicaoDados = null;
function atualizarDados() {
    if (!requisicaoDados) {
        requisicaoDados = buscarDados().finally(() => { requisicaoDados = null; });
    }
    return requisicaoDados;
}

async function buscarDados() {
    try {
        const resposta = await fetch("/dados", { cache: "no-store" });
        if (!resposta.ok) throw new Error("Falha ao consultar métricas.");
        const dados = await resposta.json();
        const { exg, textura, areaVerde, indiceSaude, statusClassificado,
                monitoramentoAtivo, cameraDisponivel, analiseValida } = resolverLeitura(dados);

        atualizarListaElementos(metricTargets.area, `${formatarNumero(areaVerde)}%`);
        atualizarListaElementos(metricTargets.exg, formatarNumero(exg));
        atualizarListaElementos(metricTargets.textura, formatarNumero(textura));

        atualizarBarrasMetricas(areaVerde, exg, textura);
        aplicarStatus(statusClassificado, analiseValida ? indiceSaude : null);
        aplicarEstadoBotao(monitoramentoAtivo, cameraDisponivel);
        atualizarRelatorio(areaVerde, exg, textura, indiceSaude, statusClassificado, dados, analiseValida);

        if (analiseValida) {
            adicionarLabel();

            adicionarPonto(historicoSaude, indiceSaude);
            adicionarPonto(historicoAreaVerde, areaVerde);
            adicionarPonto(historicoExg, exg);
            adicionarPonto(historicoTextura, textura);

            atualizarGraficos();

            aplicarTendencia("trendArea", calcularTendencia(areaVerde, historicoAreaVerde, "%"));
            aplicarTendencia("trendExg", calcularTendencia(exg, historicoExg));
            aplicarTendencia("trendTextura", calcularTendencia(textura, historicoTextura), true);

        } else {
            for (const id of ["trendArea", "trendExg", "trendTextura"]) {
                aplicarTendencia(id, { texto: "Tendência --", classe: "neutral" });
            }

        }

    } catch (erro) {
        console.error("Erro ao buscar dados:", erro);

        aplicarStatus("ERRO DE CONEXÃO");
        atualizarRelatorio(0, 0, 0, 0, "ERRO DE CONEXÃO");
        atualizarListaElementos([...metricTargets.area, ...metricTargets.exg, ...metricTargets.textura], "--");
        aplicarEstadoBotao(false, false);
        atualizarBarrasMetricas(0, 0, 0);
    }
}

async function alternarMonitoramento() {
    if (toggleMonitoramentoBtn.disabled) return;
    toggleMonitoramentoBtn.disabled = true;
    try {
        const resposta = await fetch("/toggle_monitoramento", {
            method: "POST"
        });

        if (!resposta.ok) {
            throw new Error("Falha ao alternar monitoramento.");
        }

        await resposta.json();
        if (requisicaoDados) await requisicaoDados;
        await atualizarDados();

    } catch (erro) {
        console.warn("Erro ao alternar monitoramento:", erro);
        await atualizarDados();
    } finally {
        toggleMonitoramentoBtn.disabled = false;
    }
}

toggleMonitoramentoBtn.addEventListener("click", alternarMonitoramento);

aplicarStatus("AGUARDANDO");
aplicarEstadoBotao(false, true);
atualizarBarrasMetricas(0, 0, 0);
renderizarHistoricoTabela();

atualizarDados();
setInterval(atualizarDados, 1000);

setInterval(() => {
    if (document.getElementById('tab-historico')?.classList.contains('active')) {
        renderizarHistoricoTabela();
    }
}, 10000);
