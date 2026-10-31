const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const elements = new Map();
function element(id) {
    if (!elements.has(id)) elements.set(id, {
        textContent: '', innerHTML: '', disabled: false, style: {}, children: [],
        classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
        addEventListener() {}, appendChild(child) { this.children.push(child); },
        replaceChildren() { this.children = []; }
    });
    return elements.get(id);
}
let payload = {status:'AGUARDANDO',monitoramento_ativo:true,camera_disponivel:true,analise_valida:false};
let failure = false;
const requests = [];
const context = vm.createContext({
    document: { getElementById: element, querySelectorAll: () => [], createElement: () => element(Symbol()) },
    Chart: class { constructor(_, config) { this.data=config.data; } update() {} resize() {} },
    setTimeout() {}, setInterval() {}, console: {warn(){},error(){}},
    fetch: async (url, options={}) => {
        requests.push([url, options.method || 'GET']);
        return {ok: !failure, json: async () => url === '/historico' ? [] : payload};
    },
    alert() {}, confirm: () => false
});
vm.runInContext(fs.readFileSync('static/js/dashboard.js','utf8'), context);
const run = source => vm.runInContext(source, context);
(async () => {
    await run('atualizarDados()');
    assert.equal(run('historicoSaude.length'), 0);
    assert.equal(element('statusPlanta').textContent, 'AGUARDANDO');
    assert.equal(element('relatorioIndiceSaude').textContent, '--');
    payload = {status:'ATENÇÃO', indice_saude_visual:99, area_planta:30, area_verde:90,
        verde_saudavel:65,amarelo:25,marrom:5,escuro:5,exg:150,textura:30,
        monitoramento_ativo:true,camera_disponivel:true,analise_valida:true};
    await run('atualizarDados()');
    assert.equal(element('statusPlanta').textContent, 'ATENÇÃO — 99%');
    assert.equal(element('areaVerde').textContent, '30.00%');
    assert.match(element('relatorioDiagnostico').textContent,/65.00% verde saudável/);
    assert.equal(run('historicoSaude.length'),1);
    for (const status of ['AGUARDANDO','CÂMERA INDISPONÍVEL','PLANTA NÃO DETECTADA','ERRO','ERRO NA ANÁLISE']) {
        payload = {...payload,status,analise_valida:true};
        await run('atualizarDados()');
        assert.equal(run('historicoSaude.length'),1);
        assert.equal(element('statusPlanta').textContent,status);
        assert.equal(element('relatorioIndiceSaude').textContent,'--');
        assert.equal(element('alertasLista').innerHTML,'');
    }
    assert.equal(run('resolverLeitura({status:"SAUDÁVEL", indice_saude_visual:0}).indiceSaude'),0);
    assert.equal(run('resolverLeitura({indice_saude_visual:80,monitoramento_ativo:true,camera_disponivel:true}).statusClassificado'),'SAUDÁVEL');
    assert.ok(Number.isFinite(run('resolverLeitura({indice_saude_visual:"inválido"}).indiceSaude')));
    failure = true;
    await run('atualizarDados()');
    assert.equal(element('statusPlanta').textContent,'ERRO DE CONEXÃO');
    assert.equal(element('relatorioIndiceSaude').textContent,'--');
    assert.ok(requests.every(([url,method])=>method==='GET'));
    failure = false;
    payload={status:'AGUARDANDO',monitoramento_ativo:true,camera_disponivel:true,analise_valida:false};
    await run('alternarMonitoramento()');
    assert.ok(requests.some(([url,method])=>url==='/toggle_monitoramento' && method==='POST'));
    assert.equal(element('toggleMonitoramento').disabled,false);
    console.log('Dashboard: backend prioritário, fallback, estados inválidos, relatório, gráficos, falha HTTP e toggle OK.');
})().catch(e=>{console.error(e);process.exitCode=1;});
