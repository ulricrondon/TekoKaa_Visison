const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/dashboard.js', 'utf8');
function element() {
    return { children: [], innerHTML: '', textContent: '',
        appendChild(child) { this.children.push(child); },
        replaceChildren() { this.children = []; }
    };
}
const tbody = element();
const context = vm.createContext({
    historicoTabelaBody: tbody,
    document: { createElement: element },
    formatarNumero: (n, d = 2) => Number(n).toFixed(d),
    classeHistoricoStatus: () => 'ok',
    console: { warn() {} },
    fetch: async () => ({ ok: true, json: async () => [
        { timestamp: 1000, indiceSaude: 80, areaVerde: 70, exg: 1, textura: 2, status: '<img onerror=alert(1)>' }
    ] })
});
vm.runInContext(source.slice(source.indexOf('let carregandoHistorico'), source.indexOf('function ativarAba')), context);
(async () => {
    await vm.runInContext('renderizarHistoricoTabela()', context);
    assert.equal(tbody.children.length, 1);
    assert.equal(tbody.children[0].children[1].textContent, '80%');
    assert.equal(tbody.children[0].children[5].children[0].textContent, '<img onerror=alert(1)>');
    context.fetch = async () => ({ ok: false });
    await vm.runInContext('renderizarHistoricoTabela()', context);
    assert.match(tbody.innerHTML, /indisponível/);
    context.fetch = async () => ({ ok: true, json: async () => [] });
    await vm.runInContext('renderizarHistoricoTabela()', context);
    assert.match(tbody.innerHTML, /Nenhuma análise válida/);
    console.log('Histórico frontend: renderização, erro e estado vazio OK.');
})().catch(error => { console.error(error); process.exitCode = 1; });
