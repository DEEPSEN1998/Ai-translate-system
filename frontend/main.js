/* ===============================
   CREATE LANGUAGE DROPDOWN UI
================================*/

(function createLanguageSwitcher(){

  const bar = document.createElement("div");
  bar.id = "ai-lang-switcher";

  bar.innerHTML = `
    <select id="langSelect">
      <option value="en">Lang : English</option>
      <option value="bn">Lang : Bengali</option>
      <option value="hi">Lang : Hindi</option>
    </select>
  `;

  document.body.appendChild(bar);

  const style = document.createElement("style");
  style.innerHTML = `
    #ai-lang-switcher{
      position:fixed;
      top:20px;
      right:20px;
      z-index:100000;
      background:#000;
      padding:8px 12px;
      border-radius:30px;
      box-shadow:0 0 12px rgba(0,0,0,0.5);
    }

    #ai-lang-switcher select{
      background:#000;
      color:#fff;
      border:1px solid #666;
      padding:6px 14px;
      border-radius:20px;
      outline:none;
      cursor:pointer;
    }
  `;
  document.head.appendChild(style);

  document.getElementById("langSelect")
    .addEventListener("change", translatePage);

})();


/* ===============================
   GLOBALS
================================*/

const SITE_ID = window.location.hostname;

let textNodes = [];
let originalTexts = [];
let initialized = false;


/* ===============================
   COLLECT TEXT NODES
================================*/

function collectTextNodes(){

  textNodes = [];
  originalTexts = [];

  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode(node){

        if (!node.nodeValue) return NodeFilter.FILTER_REJECT;

        const txt = node.nodeValue.trim();
        if (!txt) return NodeFilter.FILTER_REJECT;

        const parent = node.parentElement?.tagName;

        if (["SCRIPT","STYLE","NOSCRIPT","IFRAME"].includes(parent))
          return NodeFilter.FILTER_REJECT;

        return NodeFilter.FILTER_ACCEPT;
      }
    }
  );

  let node;
  while (node = walker.nextNode()){
    textNodes.push(node);
    originalTexts.push(node.nodeValue);
  }

  localStorage.setItem("originalTexts", JSON.stringify(originalTexts));
}


/* ===============================
   TRANSLATE PAGE
================================*/

async function translatePage(){

  const lang = document.getElementById("langSelect").value;

  // 🔹 FIRST TIME ONLY
  if (!initialized){
    collectTextNodes();
    initialized = true;
  }

  // 🔹 RESTORE ENGLISH
  if (lang === "en"){
    textNodes.forEach((n,i)=>{
      n.nodeValue = originalTexts[i];
    });
    return;
  }
	console.log(JSON.stringify({
        texts: originalTexts,
        target_lang: lang,
        site_id: SITE_ID
      }));
  try{
    const res = await fetch("http://127.0.0.1:8000/translate",{

      method:"POST",
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify({
        texts: originalTexts,
        target_lang: lang,
        site_id: SITE_ID
      })
    });

    const data = await res.json();
    console.log(data)
    data.translations.forEach((t,i)=>{
      textNodes[i].nodeValue = t;
    });

  }catch(err){
    console.error(err);
    alert("Translation server not running");
  }

}