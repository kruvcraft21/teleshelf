// const pdfUrl = "{{ pdf_url }}";

const frame = document.getElementById("pdfFrame");
const statusBar = document.getElementById("statusBar");
const statusText = document.getElementById("statusText");

const spinner = document.getElementById("spinner");
const check = document.getElementById("check");

const pdfUrl = frame.dataset.pdf_url

function setLoading(text) {
    spinner.style.display = "block";
    check.style.display = "none";
    statusText.textContent = text;
}

function setReady(text) {
    spinner.style.display = "none";
    check.style.display = "block";
    statusText.textContent = text;

    window.setTimeout(() => {
        statusBar.classList.add("hidden");
        frame.classList.add("status-hidden");
    }, 1200);
}

function setError(text) {
    spinner.style.display = "none";
    check.style.display = "none";
    statusText.textContent = text;
}

setLoading("Загрузка PDF-просмотрщика...");

// Корректный путь с учетом статики FastAPI
const viewerUrl = `/static/pdfjs/web/viewer.html?file=${encodeURIComponent(pdfUrl)}`;
frame.src = viewerUrl;


frame.onload = () => {
    try {
        const iframeDoc = frame.contentDocument || frame.contentWindow.document;
        const linkTag = iframeDoc.createElement('link');
        linkTag.rel = 'stylesheet';
        linkTag.href = '/static/css/toolbar.css';
        iframeDoc.head.appendChild(linkTag);
        const viewerApp = frame.contentWindow.PDFViewerApplication;
        if (viewerApp) {
            setLoading("Открытие документа...");
            viewerApp.initializedPromise.then(() => {
                viewerApp.eventBus.on("pagesinit", () => {
                    setReady("Документ открыт");
                });
            });
        }
    } catch (error) {
        setError("Ошибка инициализации просмотрщика");
    }
};
