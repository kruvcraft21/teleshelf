const tg = window.Telegram?.WebApp;
const workerTag = document.getElementById('webapp-worker');

function updateContentSafeArea() {
    const top = tg?.contentSafeAreaInset?.top ?? 0;

    document.documentElement.style.setProperty(
        "--telegram-content-safe-area-inset-top",
        `${top}px`,
    );
    window.dispatchEvent(new CustomEvent("telegram-content-safe-area-changed"));
}

if (tg) {
    updateContentSafeArea();
    tg.onEvent?.("contentSafeAreaChanged", updateContentSafeArea);
}

if (tg && tg.initData) {
    tg.ready();
    tg.expand();
    if (workerTag && workerTag.dataset.readerMode === "fullscreen") {
        tg.requestFullscreen();
    }
}
