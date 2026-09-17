import { useEffect, useState } from "react";
import { useNavigate, useLocation, Link, Routes, Route, Navigate } from "react-router-dom";
import { api } from "./api";
import { validateRegistration } from "./validation";

function Layout({ user, onLogout }) {
  const navigate = useNavigate();

  async function logout() {
    try {
      await api.logout();
    } finally {
      onLogout();
      navigate("/", { replace: true });
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <Link to={user ? "/files" : "/"}>Файловое хранилище</Link>
        </div>

        {user && (
          <nav>
            {user.is_admin && <Link to="/admin">Администрирование</Link>}
            <Link to="/files">Файлы</Link>
            <span className="user-name">{user.full_name || user.login}</span>
            <button onClick={logout}>Выйти</button>
          </nav>
        )}
      </header>

      <main className="content">
        <Routes>
          <Route
            path="/"
            element={
              user ? (
                <Navigate to={user.is_admin ? "/admin" : "/files"} replace />
              ) : (
                <Home />
              )
            }
          />

          <Route
            path="/login"
            element={
              user ? (
                <Navigate to={user.is_admin ? "/admin" : "/files"} replace />
              ) : (
                <Login onLogin={onLogout} />
              )
            }
          />

          <Route
            path="/register"
            element={
              user ? (
                <Navigate to={user.is_admin ? "/admin" : "/files"} replace />
              ) : (
                <Register />
              )
            }
          />

          <Route
            path="/files"
            element={
              user ? (
                <FileManager user={user} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />

          <Route
            path="/files/:userId"
            element={
              user ? (
                <FileManager user={user} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />

          <Route
            path="/admin"
            element={
              user?.is_admin ? (
                <Admin />
              ) : (
                <Navigate to={user ? "/files" : "/login"} replace />
              )
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function Home() {
  return (
    <div className="page-card">
      <h1>Файловое хранилище</h1>

      <p>
        Веб-система для загрузки, хранения, просмотра и скачивания файлов.
      </p>

      <div className="actions">
        <Link className="button" to="/login">
          Войти
        </Link>

        <Link className="button secondary" to="/register">
          Регистрация
        </Link>
      </div>
    </div>
  );
}

function Login({ onLogin }) {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    login: "",
    password: "",
  });

  const [error, setError] = useState("");

  function change(e) {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  }

  async function submit(e) {
    e.preventDefault();
    setError("");

    try {
      const result = await api.login(form);

      // Backend возвращает пользователя напрямую:
      // { id, login, full_name, email, is_admin, ... }
      const loggedUser = result?.user || result;

      if (!loggedUser || !loggedUser.id) {
        throw new Error("Сервер вернул некорректные данные пользователя.");
      }

      onLogin(loggedUser);

      navigate(loggedUser.is_admin ? "/admin" : "/files", {
        replace: true,
      });
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="form-card">
      <h1>Вход</h1>

      {error && <div className="error">{error}</div>}

      <form onSubmit={submit}>
        <label>
          Логин
          <input
            name="login"
            value={form.login}
            onChange={change}
            autoComplete="username"
            required
          />
        </label>

        <label>
          Пароль
          <input
            type="password"
            name="password"
            value={form.password}
            onChange={change}
            autoComplete="current-password"
            required
          />
        </label>

        <button type="submit">Войти</button>
      </form>

      <p>
        Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
      </p>
    </div>
  );
}

function Register() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    login: "",
    full_name: "",
    email: "",
    password: "",
  });

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  function change(e) {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  }

  async function submit(e) {
    e.preventDefault();
    setError("");
    setSuccess("");

    const validationError = validateRegistration(form);

    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      await api.register(form);

      setSuccess("Регистрация выполнена успешно.");

      setTimeout(() => {
        navigate("/login", { replace: true });
      }, 800);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="form-card">
      <h1>Регистрация</h1>

      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}

      <form onSubmit={submit}>
        <label>
          Логин
          <input
            name="login"
            value={form.login}
            onChange={change}
            autoComplete="username"
            required
          />
        </label>

        <label>
          ФИО
          <input
            name="full_name"
            value={form.full_name}
            onChange={change}
            required
          />
        </label>

        <label>
          Email
          <input
            type="email"
            name="email"
            value={form.email}
            onChange={change}
            autoComplete="email"
            required
          />
        </label>

        <label>
          Пароль
          <input
            type="password"
            name="password"
            value={form.password}
            onChange={change}
            autoComplete="new-password"
            required
          />
        </label>

        <button type="submit">Зарегистрироваться</button>
      </form>

      <p>
        Уже есть аккаунт? <Link to="/login">Войти</Link>
      </p>
    </div>
  );
}

function FileManager({ user }) {
  const location = useLocation();

  const selectedUserId = location.pathname.startsWith("/files/")
    ? Number(location.pathname.split("/").pop())
    : null;

  const [files, setFiles] = useState([]);
  const [storageUser, setStorageUser] = useState(user);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [uploadFile, setUploadFile] = useState(null);
  const [comment, setComment] = useState("");

  const [editing, setEditing] = useState(null);

  async function loadFiles() {
    setLoading(true);
    setError("");

    try {
      const result = await api.files(selectedUserId);

      /*
       * Поддерживаем оба варианта ответа:
       *
       * 1. Backend:
       *    [ ...files ]
       *
       * 2. Если позже API будет возвращать:
       *    { files: [...], user: {...} }
       */
      if (Array.isArray(result)) {
        setFiles(result);
      } else {
        setFiles(result?.files || []);

        if (result?.user) {
          setStorageUser(result.user);
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setStorageUser(user);
    loadFiles();
  }, [selectedUserId]);

  async function upload(e) {
    e.preventDefault();

    if (!uploadFile) {
      setError("Выберите файл.");
      return;
    }

    setError("");

    try {
      const formData = new FormData();
      formData.append("file", uploadFile);
      formData.append("comment", comment);

      await api.upload(formData, selectedUserId);

      setUploadFile(null);
      setComment("");

      const input = document.getElementById("file-upload");

      if (input) {
        input.value = "";
      }

      await loadFiles();
    } catch (err) {
      setError(err.message);
    }
  }

  async function deleteFile(id) {
    if (!window.confirm("Удалить этот файл?")) {
      return;
    }

    try {
      await api.deleteFile(id);
      await loadFiles();
    } catch (err) {
      setError(err.message);
    }
  }

  function startEdit(file) {
    setEditing({
      id: file.id,
      original_name: file.original_name,
      comment: file.comment || "",
    });
  }

  async function saveEdit() {
    if (!editing) {
      return;
    }

    try {
      await api.updateFile(editing.id, {
        // Backend ожидает поле name.
        name: editing.original_name,
        comment: editing.comment,
      });

      setEditing(null);
      await loadFiles();
    } catch (err) {
      setError(err.message);
    }
  }

  async function shareFile(id) {
    try {
      const result = await api.shareFile(id);

      const link =
        result.url ||
        result.share_url ||
        result.public_url;

      if (!link) {
        throw new Error("Сервер не вернул ссылку.");
      }

      await navigator.clipboard.writeText(
        link.startsWith("http")
          ? link
          : `${window.location.origin}${link}`
      );

      alert("Ссылка скопирована в буфер обмена.");
    } catch (err) {
      setError(err.message);
    }
  }

  function downloadFile(id) {
    window.open(`/api/files/${id}/download/`, "_blank");
  }

  function formatSize(bytes) {
    if (bytes === 0) {
      return "0 Б";
    }

    if (!bytes) {
      return "—";
    }

    const units = ["Б", "КБ", "МБ", "ГБ", "ТБ"];
    const index = Math.floor(Math.log(bytes) / Math.log(1024));

    return `${(bytes / Math.pow(1024, index)).toFixed(
      index === 0 ? 0 : 2
    )} ${units[index]}`;
  }

  function formatDate(value) {
    if (!value) {
      return "—";
    }

    return new Date(value).toLocaleString("ru-RU");
  }

  if (loading) {
    return <div className="page-card">Загрузка...</div>;
  }

  return (
    <div className="files-page">
      <div className="page-header">
        <div>
          <h1>
            Файловое хранилище
            {storageUser?.login
              ? ` — ${storageUser.login}`
              : ""}
          </h1>

          {storageUser?.full_name && (
            <p>{storageUser.full_name}</p>
          )}
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="upload-card">
        <h2>Загрузить файл</h2>

        <form onSubmit={upload}>
          <input
            id="file-upload"
            type="file"
            onChange={(e) =>
              setUploadFile(e.target.files?.[0] || null)
            }
          />

          <textarea
            placeholder="Комментарий к файлу"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />

          <button type="submit">Загрузить</button>
        </form>
      </div>

      <div className="files-card">
        <h2>Файлы</h2>

        {files.length === 0 ? (
          <p>Файлов пока нет.</p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Имя</th>
                  <th>Комментарий</th>
                  <th>Размер</th>
                  <th>Дата загрузки</th>
                  <th>Последнее скачивание</th>
                  <th>Действия</th>
                </tr>
              </thead>

              <tbody>
                {files.map((file) => (
                  <tr key={file.id}>
                    <td>{file.original_name}</td>

                    <td>{file.comment || "—"}</td>

                    <td>{formatSize(file.size)}</td>

                    <td>{formatDate(file.uploaded_at)}</td>

                    <td>{formatDate(file.last_downloaded_at)}</td>

                    <td>
                      <div className="file-actions">
                        <button
                          onClick={() => downloadFile(file.id)}
                        >
                          Скачать
                        </button>

                        <button
                          onClick={() => startEdit(file)}
                        >
                          Изменить
                        </button>

                        <button
                          onClick={() => shareFile(file.id)}
                        >
                          Ссылка
                        </button>

                        <button
                          className="danger"
                          onClick={() => deleteFile(file.id)}
                        >
                          Удалить
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {editing && (
        <div className="modal">
          <div className="modal-content">
            <h2>Редактирование файла</h2>

            <label>
              Имя файла
              <input
                value={editing.original_name}
                onChange={(e) =>
                  setEditing({
                    ...editing,
                    original_name: e.target.value,
                  })
                }
              />
            </label>

            <label>
              Комментарий
              <textarea
                value={editing.comment}
                onChange={(e) =>
                  setEditing({
                    ...editing,
                    comment: e.target.value,
                  })
                }
              />
            </label>

            <div className="actions">
              <button onClick={saveEdit}>Сохранить</button>

              <button
                className="secondary"
                onClick={() => setEditing(null)}
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Admin() {
  const navigate = useNavigate();

  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");

  async function load() {
    try {
      const result = await api.users();

      /*
       * Backend возвращает массив пользователей напрямую.
       * Оставлена совместимость с { users: [...] }.
       */
      setUsers(Array.isArray(result) ? result : result?.users || []);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function deleteUser(id) {
    if (!window.confirm("Удалить пользователя?")) {
      return;
    }

    try {
      await api.deleteUser(id);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function toggleAdmin(user) {
    try {
      await api.setAdmin(user.id, !user.is_admin);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  function formatSize(bytes) {
    if (bytes === 0) {
      return "0 Б";
    }

    if (!bytes) {
      return "—";
    }

    const units = ["Б", "КБ", "МБ", "ГБ", "ТБ"];
    const index = Math.floor(Math.log(bytes) / Math.log(1024));

    return `${(bytes / Math.pow(1024, index)).toFixed(
      index === 0 ? 0 : 2
    )} ${units[index]}`;
  }

  return (
    <div className="admin-page">
      <div className="page-header">
        <h1>Администрирование</h1>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Логин</th>
              <th>ФИО</th>
              <th>Email</th>
              <th>Администратор</th>
              <th>Файлов</th>
              <th>Размер</th>
              <th>Действия</th>
            </tr>
          </thead>

          <tbody>
            {users.map((item) => (
              <tr key={item.id}>
                <td>{item.login}</td>

                <td>{item.full_name}</td>

                <td>{item.email}</td>

                <td>
                  <input
                    type="checkbox"
                    checked={Boolean(item.is_admin)}
                    onChange={() => toggleAdmin(item)}
                  />
                </td>

                <td>{item.file_count ?? 0}</td>

                <td>
                  {formatSize(item.storage_size ?? 0)}
                </td>

                <td>
                  <div className="file-actions">
                    <button
                      onClick={() =>
                        navigate(`/files/${item.id}`)
                      }
                    >
                      Хранилище
                    </button>

                    <button
                      className="danger"
                      onClick={() => deleteUser(item.id)}
                    >
                      Удалить
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.me()
      .then((result) => {
        // Backend возвращает пользователя напрямую.
        const currentUser = result?.user || result;

        if (currentUser?.id) {
          setUser(currentUser);
        }
      })
      .catch(() => {
        setUser(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="loading-screen">
        Загрузка...
      </div>
    );
  }

  return (
    <Layout
      user={user}
      onLogout={(nextUser = null) => setUser(nextUser)}
    />
  );
}