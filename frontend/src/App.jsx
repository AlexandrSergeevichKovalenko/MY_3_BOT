import { useState } from 'react';
import { LiveKitRoom, AudioConference, ConnectionStateToast } from '@livekit/components-react';

// URL вашего сервера LiveKit
const livekitUrl = "wss://implemrntingvoicetobot-vhsnc86g.livekit.cloud";

function App() {
  // Состояние для хранения токена доступа. Изначально его нет.
  const [token, setToken] = useState(null);
  const [username, setUsername] = useState('');

  // Эта функция будет запрашивать токен с вашего бэкенда
  const handleConnect = async (e) => {
    e.preventDefault(); // Предотвращаем перезагрузку страницы при отправке формы

    if (!username) {
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
      const response = await fetch(`/api/token?username=${encodeURIComponent(username)}`);
      
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
  if (!token) {
    return (
      <div data-lk-theme="default" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <form onSubmit={handleConnect} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <h2>Присоединиться к звонку</h2>
          <input
            type="text"
            placeholder="Введите ваше имя"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={{ padding: '10px' }}
          />
          <button type="submit">Войти</button>
        </form>
      </div>
    );
  }

  // Если токен есть, отображаем комнату LiveKit
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