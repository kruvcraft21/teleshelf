const tg = window.Telegram?.WebApp;

if (tg && tg.initData) {
    tg.ready();
    tg.expand();

    const platform = tg.platform;

    // Проверяем, что это мобильная платформа (iOS или Android)
    if (platform === 'ios' || platform === 'android') {
        tg.requestFullscreen();
    }
}

// tg.MainButton.setText("Закрыть");
// tg.MainButton.show();
//
// tg.onEvent("mainButtonClicked", () => {
//     tg.sendData(JSON.stringify({
//         user_id: "{{ user_id }}",
//         book_id: "{{ book_id }}",
//         action: "closed"
//     }));
//     tg.close();
// });