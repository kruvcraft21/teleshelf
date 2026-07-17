const tg = window.Telegram?.WebApp;

if (tg && tg.initData) {
    tg.ready();
    tg.expand();


    tg.requestFullscreen();
}