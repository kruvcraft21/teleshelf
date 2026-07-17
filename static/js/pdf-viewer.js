const frame = document.getElementById("pdfFrame");
const statusBar = document.getElementById("statusBar");
const statusText = document.getElementById("statusText");

const spinner = document.getElementById("spinner");
const check = document.getElementById("check");

const session_id = frame.dataset.session_id
const current_page = frame.dataset.page
const queryString = window.location.search;
const urlParams = new URLSearchParams(queryString);
const ver = urlParams.get('v')

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
const pdfUrl = `/api/pdf/${session_id}`;
const path_to_file = session_id.length > 0 ? `file=${encodeURIComponent(pdfUrl)}#page=${current_page}` : "";
const viewerUrl = `/pdfjs/web/viewer.html?${path_to_file}`;
frame.src = viewerUrl;


frame.onload = () => {
    try {
        const iframeDoc = frame.contentDocument || frame.contentWindow.document;
        const linkTag = iframeDoc.createElement('link');
        linkTag.rel = 'stylesheet';
        linkTag.href = `/css/toolbar.css?v=${ver}`;
        iframeDoc.head.appendChild(linkTag);
        const viewerApp = frame.contentWindow.PDFViewerApplication;
        if (viewerApp) {
            setLoading("Открытие документа...");
            viewerApp.initializedPromise.then(() => {
                viewerApp.eventBus.on("pagesinit", () => {
                    setReady("Документ открыт");
                });
                viewerApp.eventBus.on("pagechanging", (event) => {
                    const page = event.pageNumber
                    const response = fetch(`api/pdf/update_position/${session_id}`, {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({ page: page })
                    })
                });
            });
        }
    } catch (error) {
        setError("Ошибка инициализации просмотрщика");
    }
};
