importScripts('https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js');
// Инициализация Firebase в Service Worker

const firebaseConfig = {
    apiKey: "AIzaSyDn0L8kb8IE9AUF548XkYsCqp24hdOJSB8",
    authDomain: "fabrika-2.firebaseapp.com",
    projectId: "fabrika-2",
    storageBucket: "fabrika-2.appspot.com",
    messagingSenderId: "94283813590",
    appId: "1:94283813590:web:f0154bdec998c293eb2f77",
    measurementId: "G-PJCMWPCFYN"
};

firebase.initializeApp(firebaseConfig);

const messaging = firebase.messaging();

// Обработка входящих уведомлений
messaging.onBackgroundMessage(function(payload) {
  console.log('[firebase-messaging-sw.js] Received background message ', payload);
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    icon: '/static/icons/icon-192x192.png'
  };

  self.registration.showNotification(notificationTitle,
    notificationOptions);
});
