"""Servidor web local do Code Doctor.

Sobe uma página no navegador onde a pessoa cola o código ou faz uma pergunta,
recebe a revisão e vê uma barra visual de consumo (tokens + custo estimado).
Trabalha só com texto colado — NÃO mexe nos arquivos do usuário, então é seguro
para quem não programa: não tem como "quebrar o projeto".

Usa apenas a biblioteca padrão (http.server) — nenhuma dependência web extra.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__, analyzer, config, providers

# Cache em memória (por sessão): trechos idênticos não são cobrados de novo.
_MEM: dict[str, dict] = {}


def _provider():
    """Monta o provedor atual, ou devolve (None, mensagem de erro amigável)."""
    config._load_dotenv()
    try:
        return providers.get_provider(), None
    except providers.ProviderError as exc:
        return None, str(exc)


def _usage_dict(u: analyzer.Usage) -> dict:
    return {"input": u.input_tokens, "output": u.output_tokens,
            "cache_read": u.cache_read_tokens}


_ALLOWED_HOSTS = {"127.0.0.1", "localhost"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silencia o log ruidoso padrão
        pass

    def _host_ok(self) -> bool:
        """Só aceita requisições cujo Host seja localhost (anti DNS-rebinding)."""
        hostname = self.headers.get("Host", "").split(":")[0]
        return hostname in _ALLOWED_HOSTS

    def _origin_ok(self) -> bool:
        """Bloqueia POST vindo de outra origem (proteção básica contra CSRF)."""
        origin = self.headers.get("Origin")
        if origin is None:
            return True  # sem Origin = não é uma página web de terceiros
        from urllib.parse import urlparse
        return urlparse(origin).hostname in _ALLOWED_HOSTS

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def do_GET(self):
        if not self._host_ok():
            self._json(403, {"error": "host não permitido"})
            return
        if self.path in ("/", "/index.html"):
            self._send(200, INDEX_HTML.encode("utf-8"),
                       "text/html; charset=utf-8")
        elif self.path == "/api/status":
            prov, err = _provider()
            self._json(200, {
                "has_key": prov is not None,
                "error": err,
                "provider": prov.name if prov else
                    os.environ.get("CODE_DOCTOR_PROVIDER", "anthropic"),
                "model": prov.model if prov else "",
                "price_in": config.price_in_per_mtok(),
                "price_out": config.price_out_per_mtok(),
                "usd_brl": config.usd_brl(),
                "version": __version__,
                "signature": __import__("code_doctor", fromlist=["SIGNATURE"]).SIGNATURE,
            })
        else:
            self._json(404, {"error": "não encontrado"})

    def do_POST(self):
        if not self._host_ok() or not self._origin_ok():
            self._json(403, {"error": "requisição não permitida"})
            return
        # Camuflagem é local e não precisa de provedor/chave.
        if self.path in ("/api/hide", "/api/reveal"):
            from . import camouflage
            data = self._read_json()
            try:
                if self.path == "/api/hide":
                    out = camouflage.hide(data.get("text", ""),
                                          data.get("style", camouflage.DEFAULT_STYLE))
                    self._json(200, {"result": out})
                else:
                    out, detected = camouflage.reveal(data.get("text", ""))
                    self._json(200, {"result": out, "style": detected})
            except ValueError as exc:
                self._json(200, {"error": str(exc)})
            return

        data = self._read_json()

        # O modelo/provedor pode vir escolhido pela interface. Se não vier,
        # usa o padrão do .env.
        prov_name = (data.get("provider") or "").strip()
        model_override = (data.get("model") or "").strip()
        if prov_name:
            try:
                provider = providers.get_provider(prov_name, model_override or None)
            except providers.ProviderError as exc:
                self._json(200, {"error": str(exc)})
                return
        else:
            provider, err = _provider()
            if provider is None:
                self._json(200, {"error": err or "Provedor não configurado."})
                return

        model = provider.model

        if self.path == "/api/review":
            code = data.get("code", "")
            filename = data.get("filename", "") or "trecho.txt"
            cache_key = "rev:" + hashlib.sha256(
                (provider.name + "|" + model + "|" + code).encode("utf-8")).hexdigest()
            if cache_key in _MEM:
                out = dict(_MEM[cache_key]); out["from_cache"] = True
                self._json(200, out)
                return
            review = analyzer.review_text(code, filename, provider)
            if not review.ok:
                self._json(200, {"error": review.error,
                                 "usage": _usage_dict(review.usage)})
                return
            out = {
                "summary": review.summary,
                "issues": [{"line": i.line, "severity": i.severity,
                            "title": i.title, "description": i.description,
                            "suggestion": i.suggestion} for i in review.issues],
                "corrected_code": review.corrected_code,
                "changed": review.changed,
                "usage": _usage_dict(review.usage),
                "from_cache": False,
            }
            _MEM[cache_key] = out
            self._json(200, out)

        elif self.path == "/api/ask":
            question = data.get("question", "")
            code = data.get("code", "")
            if not question.strip():
                self._json(200, {"error": "escreva uma pergunta"})
                return
            answer, usage, aerr = analyzer.ask(question, code, provider)
            if aerr:
                self._json(200, {"error": aerr, "usage": _usage_dict(usage)})
                return
            self._json(200, {"answer": answer, "usage": _usage_dict(usage),
                             "from_cache": False})
        else:
            self._json(404, {"error": "não encontrado"})


def serve(host: str = "127.0.0.1", port: int = 8765,
          open_browser: bool = True) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print(f"Code Doctor Web rodando em {url}")
    print("Pressione Ctrl+C para parar.")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando…")
        server.shutdown()


# ---------------------------------------------------------------------------
# Interface (HTML + CSS + JS numa página só)
# ---------------------------------------------------------------------------
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Code Doctor</title>
<style>
  :root{
    --bg:#0f1115; --panel:#171a21; --panel2:#1e222b; --line:#2a2f3a;
    --text:#e7e9ee; --muted:#9aa3b2; --accent:#5b9dff; --accent2:#7ee0a2;
    --crit:#ff5c6c; --high:#ff8a5b; --med:#ffcf5b; --low:#5bd6ff;
    --radius:14px;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);
    font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
  header{padding:20px 24px;border-bottom:1px solid var(--line);
    display:flex;align-items:center;gap:12px}
  header .logo{font-size:22px}
  header h1{font-size:18px;margin:0;font-weight:650}
  header .ver{color:var(--muted);font-size:12px;margin-left:auto}
  .wrap{max-width:920px;margin:0 auto;padding:24px}
  .tabs{display:flex;gap:8px;margin-bottom:16px}
  .tab{padding:9px 16px;border:1px solid var(--line);background:var(--panel);
    color:var(--muted);border-radius:999px;cursor:pointer;font-weight:600}
  .tab.active{color:var(--text);border-color:var(--accent);
    box-shadow:inset 0 0 0 1px var(--accent)}
  label{display:block;font-size:13px;color:var(--muted);margin:14px 0 6px}
  input[type=text],textarea{width:100%;background:var(--panel2);
    border:1px solid var(--line);color:var(--text);border-radius:10px;
    padding:11px 12px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
    font-size:13px;resize:vertical}
  textarea{min-height:180px}
  .row{display:flex;gap:12px;flex-wrap:wrap}
  .btn{margin-top:14px;background:var(--accent);color:#07101f;border:none;
    padding:12px 20px;border-radius:10px;font-weight:700;cursor:pointer;font-size:15px}
  .btn:disabled{opacity:.55;cursor:progress}
  .hint{color:var(--muted);font-size:12px;margin-top:6px}
  .banner{background:#3a2020;border:1px solid #5c2b2b;color:#ffb4b4;
    padding:12px 14px;border-radius:10px;margin-bottom:16px;display:none}
  .result{margin-top:20px;display:none}
  .card{background:var(--panel);border:1px solid var(--line);
    border-radius:var(--radius);padding:16px;margin-bottom:14px}
  .summary{color:var(--muted)}
  .issue{border-left:3px solid var(--line);padding:8px 0 8px 12px;margin:12px 0}
  .chip{display:inline-block;font-size:11px;font-weight:800;letter-spacing:.4px;
    padding:2px 8px;border-radius:6px;color:#0d0f13;margin-right:8px}
  .c-critical{background:var(--crit)} .c-high{background:var(--high)}
  .c-medium{background:var(--med)} .c-low{background:var(--low)}
  .issue .loc{color:var(--muted);font-size:12px}
  .issue .fix{color:var(--accent2);font-size:13px;margin-top:4px}
  pre{background:#0b0d11;border:1px solid var(--line);border-radius:10px;
    padding:12px;overflow:auto;font-size:12.5px;margin:0}
  .code-head{display:flex;align-items:center;gap:8px;margin-bottom:8px}
  .mini{background:var(--panel2);border:1px solid var(--line);color:var(--text);
    padding:6px 10px;border-radius:8px;cursor:pointer;font-size:12px}
  .ok{color:var(--accent2)}
  /* Barra de consumo */
  .meter{position:sticky;bottom:0;margin-top:24px;background:var(--panel);
    border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px}
  .meter .top{display:flex;justify-content:space-between;align-items:baseline;
    font-size:13px;color:var(--muted);margin-bottom:8px;gap:10px;flex-wrap:wrap}
  .bar{height:12px;background:var(--panel2);border-radius:999px;overflow:hidden;
    border:1px solid var(--line)}
  .bar>span{display:block;height:100%;width:0;background:var(--accent2);
    transition:width .4s ease}
  .meter .foot{display:flex;justify-content:space-between;margin-top:8px;
    font-size:12px;color:var(--muted);gap:10px;flex-wrap:wrap;align-items:center}
  .meter input[type=text]{width:70px;display:inline-block;padding:4px 6px;
    font-family:inherit;font-size:12px}
  a{color:var(--accent)}
</style>
</head>
<body>
<header>
  <span class="logo">🩺</span>
  <h1>Code Doctor</h1>
  <span class="ver" id="ver"></span>
</header>

<div class="wrap">
  <div class="banner" id="banner"></div>

  <div class="tabs">
    <div class="tab active" data-mode="review">Revisar código</div>
    <div class="tab" data-mode="ask">Tirar dúvida</div>
    <div class="tab" data-mode="hide">🕵️ Camuflar</div>
  </div>

  <div id="model-bar" style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:16px;padding:10px 12px;background:var(--panel);border:1px solid var(--line);border-radius:10px">
    <span style="color:var(--muted);font-size:13px">Modelo:</span>
    <select id="modelo" style="background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:7px 10px">
      <option value="sonnet">Melhor qualidade ($2/$10 por 1M)</option>
      <option value="haiku">Mais econômico ($1/$5 por 1M)</option>
      <option value="ollama">Grátis — roda no seu PC (Ollama)</option>
    </select>
    <input type="text" id="ollamaModel" value="llama3.1" placeholder="modelo do Ollama"
      style="display:none;background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:7px 10px;width:150px">
    <span id="modelo-hint" style="color:var(--muted);font-size:12px"></span>
  </div>

  <!-- REVIEW -->
  <div id="pane-review">
    <label>Nome do arquivo (opcional — ajuda a detectar a linguagem)</label>
    <input type="text" id="filename" placeholder="ex.: app.py, index.js">
    <label>Cole o código para revisar</label>
    <textarea id="code" placeholder="cole aqui seu código…"></textarea>
    <div class="hint">Seu código fica só no seu computador. Nada é salvo nem enviado além da análise.</div>
    <button class="btn" id="btn-review">Revisar</button>
  </div>

  <!-- ASK -->
  <div id="pane-ask" style="display:none">
    <label>Sua pergunta</label>
    <textarea id="question" style="min-height:80px" placeholder="ex.: por que essa função dá erro quando a lista está vazia?"></textarea>
    <label>Código relacionado (opcional)</label>
    <textarea id="code2" placeholder="cole o código, se a dúvida for sobre ele…"></textarea>
    <button class="btn" id="btn-ask">Perguntar</button>
  </div>

  <!-- CAMUFLAR -->
  <div id="pane-hide" style="display:none">
    <label>Cole o código para camuflar (ou o texto secreto para revelar)</label>
    <textarea id="secret" placeholder="cole aqui…"></textarea>
    <div class="row" style="align-items:center;margin-top:6px">
      <span style="color:var(--muted);font-size:13px">Idioma secreto:</span>
      <select id="style" style="background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:7px 10px">
        <option value="runas">ᚠ Runas</option>
        <option value="katakana">ア Katakana</option>
        <option value="braille">⠿ Braille</option>
        <option value="emoji">😀 Emoji</option>
      </select>
    </div>
    <div class="row">
      <button class="btn" id="btn-hide">🔒 Camuflar</button>
      <button class="btn" id="btn-reveal" style="background:var(--accent2)">🔓 Revelar</button>
    </div>
    <div class="hint">100% local — não usa a API, não gasta nada. É camuflagem, não
      criptografia: qualquer um com esta ferramenta revela. Serve para disfarçar/brincar,
      não para guardar segredos de verdade.</div>
  </div>

  <div class="result" id="result"></div>

  <!-- MEDIDOR DE CONSUMO -->
  <div class="meter">
    <div class="top">
      <span><b id="cost-session">$0.0000</b> gastos nesta sessão (estimado)</span>
      <span id="tok-session">0 tokens</span>
    </div>
    <div class="bar"><span id="bar-fill"></span></div>
    <div class="foot">
      <span>Orçamento da sessão: $<input type="text" id="budget" value="0.50"></span>
      <span id="last-call">—</span>
    </div>
    <div class="hint" style="margin-top:8px">
      Estimativa = tokens usados × preço do modelo. Não é o saldo real da sua conta
      (a API não informa isso); é um guia de gasto. Ajuste preços por variável de ambiente.
    </div>
  </div>
  <div style="max-width:920px;margin:0 auto;padding:0 24px 28px;color:var(--muted);font-size:12px" id="sig"></div>
</div>

<script>
let PRICE_IN=2.0, PRICE_OUT=10.0;      // por milhão de tokens (padrão Sonnet 5)
let USD_BRL=5.17;                       // cotação dólar→real (vem do servidor)
let sessTokens=0, sessCost=0;

// Modelos que a pessoa pode escolher na interface.
const MODELS = {
  sonnet: {provider:'anthropic', model:'claude-sonnet-5',            pin:2, pout:10, hint:'Melhor qualidade. Bom pra revisões difíceis.'},
  haiku:  {provider:'anthropic', model:'claude-haiku-4-5-20251001',  pin:1, pout:5,  hint:'Metade do preço. Ótimo pro dia a dia.'},
  ollama: {provider:'ollama',    model:'',                           pin:0, pout:0,  hint:'Grátis! Precisa do Ollama instalado e rodando no seu PC.'},
};

function currentChoice(){
  const k=document.getElementById('modelo').value;
  const m=MODELS[k];
  const model = k==='ollama'
    ? (document.getElementById('ollamaModel').value.trim() || 'llama3.1')
    : m.model;
  return {provider:m.provider, model};
}

function onModelChange(){
  const k=document.getElementById('modelo').value;
  const m=MODELS[k];
  PRICE_IN=m.pin; PRICE_OUT=m.pout;
  document.getElementById('ollamaModel').style.display = k==='ollama' ? '' : 'none';
  document.getElementById('modelo-hint').textContent = m.hint;
}

async function loadStatus(){
  try{
    const s=await (await fetch('/api/status')).json();
    document.getElementById('ver').textContent='v'+s.version;
    PRICE_IN=s.price_in; PRICE_OUT=s.price_out;
    if(s.usd_brl){ USD_BRL=s.usd_brl; }
    if(s.signature){ document.getElementById('sig').textContent=s.signature; }
    if(!s.has_key){
      const b=document.getElementById('banner');
      b.style.display='block';
      b.textContent='⚠ '+(s.error || 'Provedor não configurado.')+' Ajuste as variáveis de ambiente (ou o .env) e reinicie.';
    }
  }catch(e){}
}
loadStatus();

// troca de abas
document.querySelectorAll('.tab').forEach(t=>{
  t.onclick=()=>{
    document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
    t.classList.add('active');
    const m=t.dataset.mode;
    document.getElementById('pane-review').style.display = m==='review'?'':'none';
    document.getElementById('pane-ask').style.display = m==='ask'?'':'none';
    document.getElementById('pane-hide').style.display = m==='hide'?'':'none';
  };
});

function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}

function brl(usd){ return (usd*USD_BRL).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2}); }
function updateMeter(u, fromCache){
  const inTok=u.input||0, outTok=u.output||0;
  const cost=(inTok/1e6)*PRICE_IN + (outTok/1e6)*PRICE_OUT;
  if(!fromCache){ sessTokens+=inTok+outTok; sessCost+=cost; }
  document.getElementById('tok-session').textContent=sessTokens.toLocaleString('pt-BR')+' tokens';
  document.getElementById('cost-session').textContent='$'+sessCost.toFixed(4)+' (≈ R$ '+brl(sessCost)+')';
  const budget=parseFloat(document.getElementById('budget').value)||0.5;
  const pct=Math.min(100,(sessCost/budget)*100);
  const fill=document.getElementById('bar-fill');
  fill.style.width=pct+'%';
  fill.style.background = pct>90?'var(--crit)':pct>66?'var(--high)':'var(--accent2)';
  document.getElementById('last-call').textContent = fromCache
    ? 'última: memória (0 tokens)'
    : 'última: '+inTok+' entrada / '+outTok+' saída · $'+cost.toFixed(4)+' (≈ R$ '+brl(cost)+')';
}

function showError(msg){
  const r=document.getElementById('result'); r.style.display='block';
  r.innerHTML='<div class="card" style="border-color:#5c2b2b;color:#ffb4b4">'+esc(msg)+'</div>';
}

function maybeOllamaHint(msg){
  if(document.getElementById('modelo').value==='ollama'){
    return msg + '  —  Dica: o Ollama precisa estar instalado e rodando. No terminal, rode: code-doctor instalar-ollama  (ou baixe em ollama.com).';
  }
  return msg;
}

async function doReview(){
  const btn=document.getElementById('btn-review');
  const code=document.getElementById('code').value;
  if(!code.trim()){showError('Cole algum código para revisar.');return;}
  btn.disabled=true; btn.textContent='Analisando…';
  try{
    const res=await fetch('/api/review',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({code, filename:document.getElementById('filename').value, ...currentChoice()})});
    const d=await res.json();
    if(d.usage) updateMeter(d.usage, d.from_cache);
    if(d.error){showError(maybeOllamaHint(d.error));return;}
    renderReview(d);
  }catch(e){showError('Falha de conexão com o servidor.');}
  finally{btn.disabled=false; btn.textContent='Revisar';}
}

function renderReview(d){
  const r=document.getElementById('result'); r.style.display='block';
  let html='<div class="card"><div class="summary">'+esc(d.summary||'')+'</div>';
  if(!d.issues||!d.issues.length){
    html+='<p class="ok">✓ Nenhum problema encontrado.</p>';
  }else{
    const order={critical:0,high:1,medium:2,low:3};
    d.issues.sort((a,b)=>(order[a.severity]??9)-(order[b.severity]??9));
    const lbl={critical:'CRÍTICO',high:'ALTO',medium:'MÉDIO',low:'BAIXO'};
    for(const i of d.issues){
      html+='<div class="issue"><span class="chip c-'+i.severity+'">'+(lbl[i.severity]||i.severity)+'</span>'
        +'<b>'+esc(i.title)+'</b> <span class="loc">('+(i.line?'linha '+i.line:'geral')+')</span>'
        +'<div>'+esc(i.description)+'</div>'
        +(i.suggestion?'<div class="fix">→ '+esc(i.suggestion)+'</div>':'')+'</div>';
    }
  }
  html+='</div>';
  if(d.changed && d.corrected_code){
    html+='<div class="card"><div class="code-head"><b>Código corrigido</b>'
      +'<button class="mini" onclick="copyCode(this)">copiar</button>'
      +'<button class="mini" onclick="downloadCode()">baixar</button></div>'
      +'<pre id="fixed">'+esc(d.corrected_code)+'</pre></div>';
  }
  r.innerHTML=html;
  window._fixed=d.corrected_code||''; window._fname=document.getElementById('filename').value||'corrigido.txt';
}

function copyCode(btn){navigator.clipboard.writeText(window._fixed||'');btn.textContent='copiado!';setTimeout(()=>btn.textContent='copiar',1500);}
function downloadCode(){const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([window._fixed||''],{type:'text/plain'}));
  a.download=window._fname; a.click();}

async function doAsk(){
  const btn=document.getElementById('btn-ask');
  const question=document.getElementById('question').value;
  if(!question.trim()){showError('Escreva uma pergunta.');return;}
  btn.disabled=true; btn.textContent='Pensando…';
  try{
    const res=await fetch('/api/ask',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({question, code:document.getElementById('code2').value, ...currentChoice()})});
    const d=await res.json();
    if(d.usage) updateMeter(d.usage, d.from_cache);
    if(d.error){showError(maybeOllamaHint(d.error));return;}
    const r=document.getElementById('result'); r.style.display='block';
    r.innerHTML='<div class="card"><div style="white-space:pre-wrap">'+esc(d.answer)+'</div></div>';
  }catch(e){showError('Falha de conexão com o servidor.');}
  finally{btn.disabled=false; btn.textContent='Perguntar';}
}

async function doCamouflage(op){
  const text=document.getElementById('secret').value;
  if(!text.trim()){showError('Cole algum texto.');return;}
  const style=document.getElementById('style').value;
  try{
    const res=await fetch('/api/'+(op==='hide'?'hide':'reveal'),{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({text, style})});
    const d=await res.json();
    if(d.error){showError(d.error);return;}
    const r=document.getElementById('result'); r.style.display='block';
    const label = op==='hide' ? 'Código camuflado ('+style+')'
                              : 'Código revelado (idioma: '+d.style+')';
    r.innerHTML='<div class="card"><div class="code-head"><b>'+label+'</b>'
      +'<button class="mini" onclick="copyResult(this)">copiar</button></div>'
      +'<pre id="camout" style="white-space:pre-wrap;word-break:break-word">'+esc(d.result)+'</pre></div>';
    window._camout=d.result;
    // após camuflar, joga o resultado no campo para você poder Revelar em seguida
    if(op==='hide'){ document.getElementById('secret').value=d.result; }
  }catch(e){showError('Falha de conexão com o servidor.');}
}
function copyResult(btn){navigator.clipboard.writeText(window._camout||'');btn.textContent='copiado!';setTimeout(()=>btn.textContent='copiar',1500);}

document.getElementById('btn-hide').onclick=()=>doCamouflage('hide');
document.getElementById('btn-reveal').onclick=()=>doCamouflage('reveal');

document.getElementById('btn-review').onclick=doReview;
document.getElementById('btn-ask').onclick=doAsk;
document.getElementById('budget').oninput=()=>updateMeter({input:0,output:0}, true);
document.getElementById('modelo').onchange=onModelChange;
document.getElementById('ollamaModel').oninput=()=>{};
onModelChange();  // inicializa dica e preços
</script>
</body>
</html>"""
