import os
import re
import tempfile
import requests
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from markitdown import MarkItDown

app = FastAPI(title="MarkItDown Web UI")
md = MarkItDown()

class ConvertRequest(BaseModel):
    url: str

def convert_google_url(url: str) -> str:
    """將 Google 文件分享連結自動轉換為直接匯出/下載格式"""
    doc_match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', url)
    if doc_match:
        return f"https://docs.google.com/document/d/{doc_match.group(1)}/export?format=pdf"

    sheet_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    if sheet_match:
        return f"https://docs.google.com/spreadsheets/d/{sheet_match.group(1)}/export?format=xlsx"

    slide_match = re.search(r'/presentation/d/([a-zA-Z0-9-_]+)', url)
    if slide_match:
        return f"https://docs.google.com/presentation/d/{slide_match.group(1)}/export/pdf"

    return url

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTML_CONTENT

@app.post("/api/convert/url")
async def convert_by_url(req: ConvertRequest):
    target_url = convert_google_url(req.url.strip())
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(target_url, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"無法抓取該網址 (HTTP {resp.status_code})，請確認檔案分享權限已開啟（公開 / 知道連結者可檢視）")

        suffix = ".bin"
        if "pdf" in target_url:
            suffix = ".pdf"
        elif "xlsx" in target_url:
            suffix = ".xlsx"
        elif not target_url.endswith((".pdf", ".docx", ".pptx", ".xlsx", ".html")):
            suffix = ".html"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(resp.content)
            tmp_path = tmp.name

        result = md.convert(tmp_path)
        os.remove(tmp_path)
        return {"markdown": result.text_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"轉換失敗: {str(e)}")

@app.post("/api/convert/file")
async def convert_by_file(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename)[1]
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        result = md.convert(tmp_path)
        os.remove(tmp_path)
        return {"markdown": result.text_content, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"轉換失敗: {str(e)}")

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MarkItDown 文件轉換器</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 min-h-screen text-slate-800 p-6 flex justify-center">
  <div class="max-w-4xl w-full bg-white rounded-xl shadow-md p-6 space-y-6">
    <div class="border-b pb-4">
      <h1 class="text-2xl font-bold text-indigo-600 flex items-center gap-2">
        📄 MarkItDown 萬能轉換器
      </h1>
      <p class="text-sm text-slate-500 mt-1">
        支援 PDF、網頁、Google Docs / Sheets / Slides 網址（需開啟連結共用檢視權限）
      </p>
    </div>

    <div class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1">貼上網址 / 雲端文件連結</label>
        <div class="flex gap-2">
          <input type="text" id="urlInput" placeholder="https://docs.google.com/... 或 https://example.com" class="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 border-slate-300">
          <button id="btnConvertUrl" onclick="convertUrl()" class="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-5 py-2 rounded-lg transition">轉換網址</button>
        </div>
      </div>

      <div class="flex items-center gap-4 text-xs text-slate-400">
        <div class="flex-1 border-t border-slate-200"></div>
        <span>或直接上傳本機檔案</span>
        <div class="flex-1 border-t border-slate-200"></div>
      </div>

      <div>
        <label class="block text-sm font-medium text-slate-700 mb-1">上傳本機檔案 (PDF, DOCX, PPTX, XLSX, HTML, 圖片等)</label>
        <input type="file" id="fileInput" onchange="convertFile()" class="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer">
      </div>
    </div>

    <div id="loading" class="hidden text-center py-4">
      <span class="inline-block animate-spin rounded-full h-6 w-6 border-2 border-indigo-600 border-t-transparent"></span>
      <p class="text-sm text-slate-500 mt-2">正在抓取並轉換文件中，請稍候...</p>
    </div>

    <div id="outputArea" class="hidden space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="text-md font-semibold text-slate-700">轉換結果 (Markdown)</h2>
        <div class="flex gap-2">
          <button onclick="copyToClipboard()" class="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium px-3 py-1.5 rounded border border-slate-300 flex items-center gap-1 transition">
            📋 複製內容
          </button>
          <button onclick="downloadMarkdown()" class="bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-medium px-3 py-1.5 rounded border border-indigo-200 flex items-center gap-1 transition">
            💾 下載 .md 檔
          </button>
        </div>
      </div>
      <textarea id="resultText" rows="16" class="w-full font-mono text-xs bg-slate-900 text-slate-100 p-4 rounded-lg focus:outline-none resize-y"></textarea>
    </div>
  </div>

  <script>
    async function convertUrl() {
      const url = document.getElementById('urlInput').value.trim();
      if (!url) return alert('請先輸入網址！');
      executeConversion('/api/convert/url', { url });
    }

    async function convertFile() {
      const file = document.getElementById('fileInput').files[0];
      if (!file) return;
      const formData = new FormData();
      formData.append('file', file);
      executeConversion('/api/convert/file', formData, true);
    }

    async function executeConversion(endpoint, bodyData, isFormData = false) {
      const loading = document.getElementById('loading');
      const outputArea = document.getElementById('outputArea');
      const resultText = document.getElementById('resultText');

      loading.classList.remove('hidden');
      outputArea.classList.add('hidden');

      try {
        const options = { method: 'POST' };
        if (isFormData) {
          options.body = bodyData;
        } else {
          options.headers = { 'Content-Type': 'application/json' };
          options.body = JSON.stringify(bodyData);
        }

        const res = await fetch(endpoint, options);
        const data = await res.json();

        if (!res.ok) throw new Error(data.detail || '轉換失敗');

        resultText.value = data.markdown;
        outputArea.classList.remove('hidden');
      } catch (err) {
        alert(err.message);
      } finally {
        loading.classList.add('hidden');
      }
    }

    function copyToClipboard() {
      const text = document.getElementById('resultText').value;
      navigator.clipboard.writeText(text).then(() => alert('已成功複製 Markdown 內容！'));
    }

    function downloadMarkdown() {
      const text = document.getElementById('resultText').value;
      const blob = new Blob([text], { type: 'text/markdown;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `converted_${Date.now()}.md`;
      a.click();
      URL.revokeObjectURL(url);
    }
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
