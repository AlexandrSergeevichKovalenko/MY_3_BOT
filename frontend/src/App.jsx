import { useState } from 'react';
import { LiveKitRoom, AudioConference, ConnectionStateToast } from '@livekit/components-react';

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
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

      const response = await fetch(
        `${API_BASE_URL}/api/token?user_id=${encodeURIComponent(telegramID)}&username=${encodeURIComponent(username)}`
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
      <div data-lk-theme="default" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <form onSubmit={handleConnect} style={{ display: 'flex', flexDirection: 'column', gap: '15px', width: '300px' }}>
          <h2 style={{ textAlign: 'center', color: 'white' }}>Вход в урок</h2>
          
          {/* ПОЛЕ 1: Telegram ID */}
          <input
            type="text"
            placeholder="Ваш Telegram ID (цифры)"
            value={telegramID}
            onChange={(e) => setTelegramID(e.target.value)}
            style={{ padding: '12px', borderRadius: '5px', border: 'none' }}
          />

          {/* ПОЛЕ 2: Имя */}
          <input
            type="text"
            placeholder="Как вас называть? (Имя)"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={{ padding: '12px', borderRadius: '5px', border: 'none' }}
          />

          <button type="submit" style={{ padding: '12px', cursor: 'pointer', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '5px', fontWeight: 'bold' }}>
            Начать урок
          </button>
        </form>
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
    >
      <AudioConference />
      <ConnectionStateToast />
    </LiveKitRoom>
  );
}

export default App;