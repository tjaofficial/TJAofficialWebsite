document.addEventListener("DOMContentLoaded", function () {
    const qrContainer = document.getElementById("hunt-qr-code");
    if (!qrContainer) return;

    const qrToken = qrContainer.dataset.qrToken;
    if (!qrToken) return;

    const qrPayload = JSON.stringify({
        type: "nfc_hunt",
        token: qrToken
    });

    qrContainer.innerHTML = "";

    new QRCode(qrContainer, {
        text: qrPayload,
        width: 220,
        height: 220,
        correctLevel: QRCode.CorrectLevel.H
    });
});