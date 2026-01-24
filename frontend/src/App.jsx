import { useState } from 'react';
import {
  LiveKitRoom,
  ControlBar,
  ConnectionStateToast,
  RoomAudioRenderer,
} from '@livekit/components-react';
import '@livekit/components-styles';
import './App.css';

// URL вашего сервера LiveKit
const livekitUrl = "wss://implemrntingvoicetobot-vhsnc86g.livekit.cloud";

function App() {
  // Состояние для хранения токена доступа. Изначально его нет.
  // Мы говорим React'у: "Создай ячейку памяти. Изначально положи туда null (пустоту)".
  // Когда мы захотим обновить эту ячейку, мы будем использовать функцию setToken.
  // Каждый раз, когда мы вызываем setToken с новым значением, React "замечает" это изменение
  // и перерисовывает компонент App с новым значением token.
  // Аналогично: const [username, setUsername] = useState(''); — создали память для имени пользователя, изначально пустая строка.
  // Итог: useState — это способ "создать память" внутри функционального компонента React.
  const [token, setToken] = useState(null);

  const [telegramID, setTelegramID] = useState('');
  const [username, setUsername] = useState('');

  // Эта функция будет запрашивать токен с вашего бэкенда
  const handleConnect = async (e) => {
    e.preventDefault(); // Предотвращаем перезагрузку страницы при отправке формы
    // Простая валидация: проверяем, что имя пользователя введено
    if (!telegramID || !username) {
      alert('Пожалуйста, введите ваше имя');
      return;
    }

    try {
      // Отправляем запрос на ваш бэкенд для получения токена.
      // Итог: "Эндпоинт" — это просто уникальный адресуемый маршрут на вашем 
      // сервере, который привязан к конкретной функции, отвечающей за 
      // обработку запросов именно по этому маршруту. Это способ организовать 
      // разные функции вашего бэкенда.
      // Ваш Flask-сервер — это "администратор" на ресепшене. 
      // У него есть список всех "кабинетов" и того, кто за них отвечает. 
      // Этот список создается с помощью декораторов @app.route().
      // Когда фронтенд делает fetch на http://localhost:5001/token, 
      // запрос прилетает на "ресепшен"."Администратор" (Flask) 
      // смотрит на запрошенный путь (/token).
      // Он заглядывает в свой список и видит: "Ага, за 
      // кабинет /token отвечает функция get_token".
      // Он "направляет" этот запрос на выполнение в функцию get_token.
      // Функция get_token выполняется, генерирует токен и возвращает его обратно 
      // "администратору" (Flask), который в свою очередь отправляет этот токен 
      // обратно фронтенду как ответ на запрос fetch.
      // Таким образом, "эндпоинт" — это просто адрес, по которому фронтенд 
      // может обратиться к определенной функции на бэкенде.
      // В нашем случае этот адрес — /token, а функция — get_token.
      // Вот так фронтенд и бэкенд "общаются" друг с другом через эти эндпоинты.

      const response = await fetch(
        `/api/token?user_id=${encodeURIComponent(telegramID)}&username=${encodeURIComponent(username)}`
      );
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Ошибка получения токена: ${errorText}`);
      }
      
      const data = await response.json();
      
      // Сохраняем полученный токен в состояние, что вызовет перерисовку компонента
      setToken(data.token);

    } catch (error) {
      console.error(error);
      alert(error.message);
    }
  };

  // Если токена еще нет, показываем форму для входа
  // <form>: Это HTML-тег для сбора данных. Его особенность: он умеет реагировать на нажатие клавиши Enter на клавиатуре.
  // Когда пользователь нажимает Enter, форма автоматически вызывает функцию, указанную в onSubmit.
  // В нашем случае это handleConnect.
  // Таким образом, пользователь может либо нажать кнопку "Войти",
  // либо просто нажать Enter после ввода имени, и форма все равно сработает.
  // onSubmit — это событие "Отправка формы" (когда нажали кнопку submit или Enter).
  // e.preventDefault() внутри handleConnect предотвращает стандартное поведение формы — перезагрузку страницы.
  // {handleConnect} — мы говорим: "Когда случится отправка, НЕ перезагружай страницу (как делают старые сайты), а запусти нашу функцию handleConnect".
  // <h2>: Header 2. Заголовок второго уровня (жирный, крупный текст). Просто надпись.
  // Поле ввода <input> (Связь с памятью):
  // Это самая сложная концепция React, называется "Управляемый компонент" (Controlled Component).
  // Идея в том, что значение поля ввода (input) "связывается" с состоянием React (переменная username).
  // Когда пользователь вводит текст, срабатывает событие onChange.
  // Мы ловим это событие и вызываем setUsername с новым значением e.target.value.
  // Это обновляет состояние username в React.
  // Поскольку состояние изменилось, React перерисовывает компонент App,
  // и новое значение username снова "попадает" в поле ввода через атрибут value={username}.
  // Таким образом, поле ввода всегда "отражает" текущее состояние username.
  // Итог: Поле ввода и состояние username "связаны" друг с другом.
  // Любое изменение в поле ввода обновляет состояние,
  // а любое изменение состояния обновляет отображаемое значение в поле ввода.
  // Это позволяет нам точно контролировать, что находится в поле ввода в любой момент времени.
  // Кнопка <button type="submit">: Кнопка для отправки формы. При нажатии запускается событие onSubmit формы, вызывая handleConnect.
if (!token) {
    return (
      <div className="lesson-page lesson-login" data-lk-theme="default">
        <div className="lesson-bg" aria-hidden="true" />
        <div className="login-card">
          <div className="login-header">
            <span className="pill">Deutsch Tutor</span>
            <h2>Вход в урок</h2>
            <p>Подключитесь к разговорной практике и начните диалог с учителем.</p>
          </div>
          <form onSubmit={handleConnect} className="login-form">
            <label className="field">
              <span>Telegram ID</span>
              <input
                type="text"
                placeholder="Ваш Telegram ID (цифры)"
                value={telegramID}
                onChange={(e) => setTelegramID(e.target.value)}
              />
            </label>

            <label className="field">
              <span>Ваше имя</span>
              <input
                type="text"
                placeholder="Как вас называть? (Имя)"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>

            <button type="submit" className="primary-button">
              Начать урок
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <LiveKitRoom
      serverUrl={livekitUrl}
      token={token}
      connect={true}
      audio={true}
      video={false}
      onDisconnected={() => setToken(null)}
      onError={(e) => console.error("LiveKit error:", e)}
      className="lesson-page lesson-room"
      data-lk-theme="default"
    >
      <div className="lesson-bg" aria-hidden="true" />
      <div className="lesson-shell">
        <header className="lesson-header">
          <div>
            <span className="pill">Учитель онлайн</span>
            <h1>Живая практика немецкого</h1>
            <p>Говорите свободно, а помощник ведет диалог, исправляет и поддерживает.</p>
          </div>
          <div className="lesson-meta">
            <span>Пользователь: {username}</span>
            <span>ID: {telegramID}</span>
          </div>
        </header>

        <main className="lesson-main">
          <section className="lesson-hero">
            <div className="lesson-illustration" aria-hidden="true">
              <svg viewBox="0 0 320 320" role="img">
                <defs>
                  <linearGradient id="bookGlow" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#ffb347" />
                    <stop offset="100%" stopColor="#ff7e5f" />
                  </linearGradient>
                </defs>
                <circle cx="160" cy="160" r="120" fill="#fff1d6" />
                <path d="M95 110c0-12 10-22 22-22h58c12 0 22 10 22 22v100c0 8-6 15-14 16-20 2-44 2-66 0-12-1-22-10-22-22z" fill="url(#bookGlow)" />
                <path d="M185 88h32c12 0 22 10 22 22v100c0 12-10 22-22 22h-32" fill="#ffd7aa" />
                <path d="M120 135h60M120 165h60M120 195h50" stroke="#6b3a1a" strokeWidth="6" strokeLinecap="round" />
                <circle cx="210" cy="90" r="26" fill="#6b3a1a" />
                <path d="M198 86h24v8h-24zM210 72v32" fill="#fff1d6" />
              </svg>
            </div>
            <div className="lesson-copy">
              <h2>Сфокусируйтесь на голосе</h2>
              <p>Нажмите на микрофон, чтобы включить речь, и нажмите выход, когда урок завершен.</p>
              <div className="lesson-tips">
                <div className="tip">Четко формулируйте ответы, чтобы учитель слышал интонацию.</div>
                <div className="tip">Если нужно подумать, просто сделайте паузу — связь сохранится.</div>
              </div>
            </div>
          </section>

          <section className="lesson-controls">
            <h3>Управление уроком</h3>
            <p>Все основные действия собраны в центре: микрофон, выход и настройки.</p>
            <div className="lesson-control-bar">
              <ControlBar />
            </div>
            <div className="lesson-hint">Совет: держите окно открытым, чтобы учитель не прерывал сессию.</div>
          </section>
        </main>
      </div>

      <RoomAudioRenderer />
      <ConnectionStateToast />
    </LiveKitRoom>
  );
}

export default App;
