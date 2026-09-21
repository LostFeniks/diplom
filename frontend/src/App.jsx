import React, { useEffect, useState } from "react";
import {
  Link,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import { api } from "./api";
import { validateRegistration } from "./validation";

function Layout({ user, onLogout, children }) {
  return (
    <div className="app">
      <header>
        <Link className="brand" to="/">
          Файловое хранилище
        </Link>

        <nav>
          <Link to="/">Главная</Link>

          {user ? (
            <>
              <Link to="/files">Мои файлы</Link>

              {user.is_admin && (
                <Link to="/admin">Администрирование</Link>
              )}

              <span className="user-badge">{user.login}</span>

              <button className="link-button" onClick={onLogout}>
                Выход
              </button>
            </>
          ) : (
            <>
              <Link to="/login">Вход</Link>
              <Link to="/register">Регистрация</Link>
            </>
          )}
        </nav>
      </header>

      <main>{children}</main>

      <footer>
        Дипломный проект · Django + PostgreSQL + React
      </footer>
    </div>
  );
}

function Home({ user }) {
  return (
    <section className="hero">
      <div className="card">
        <h1>Файловое хранилище</h1>

        <p>
          Загружайте, храните, переименовывайте и скачивайте свои файлы.
        </p>

        <p>
          Для каждого файла можно добавить комментарий и сформировать
          обезличенную публичную ссылку.
        </p>

        <div className="actions">
          {user ? (
            <Link className="button" to="/files">
              Открыть хранилище
            </Link>
          ) : (
            <>
              <Link className="button" to="/register">
                Регистрация
              </Link>

              <Link className="button secondary" to="/login">
                Вход
              </Link>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

function FormError({ error }) {
  return error ? <div className="error">{error}</div> : null;
}

function Register() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    login: "",
    full_name: "",
    email: "",
    password: "",
  });

  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState("");

  function change(e) {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });

    setErrors({
      ...errors,
      [e.target.name]: "",
    });
  }

  async function submit(e) {
    e.preventDefault();

    const clientErrors = validateRegistration(form);

    setErrors(clientErrors);

    if (Object.keys(clientErrors).length) {
      return;
    }

    try {
      await api.register(form);

      navigate("/login", {
        state: {
          registered: true,
        },
      });
    } catch (err) {
      setServerError(err.message);
    }
  }

  return (
    <FormCard title="Регистрация">
      <form onSubmit={submit}>
        <label>
          Логин
          <input
            name="login"
            value={form.login}
            onChange={change}
            autoComplete="username"
          />
        </label>

        <FormError error={errors.login} />

        <label>
          Полное имя
          <input
            name="full_name"
            value={form.full_name}
            onChange={change}
          />
        </label>

        <FormError error={errors.full_name} />

        <label>
          Email
          <input
            type="email"
            name="email"
            value={form.email}
            onChange={change}
            autoComplete="email"
          />
        </label>

        <FormError error={errors.email} />

        <label>
          Пароль
          <input
            type="password"
            name="password"
            value={form.password}
            onChange={change}
            autoComplete="new-password"
          />
        </label>

        <FormError error={errors.password} />
        <FormError error={serverError} />

        <button className="button" type="submit">
          Зарегистрироваться
        </button>
      </form>
    </FormCard>
  );
}

function Login({ onLogin }) {
  const navigate = useNavigate();
  const location = useLocation();

  const [form, setForm] = useState({
    login: "",
    password: "",
  });

  const [error, setError] = useState("");

  const registered = location.state?.registered;

  async function submit(e) {
    e.preventDefault();
    setError("");

    try {
      const result = await api.login(form);

      onLogin(result.user);

      navigate(
        result.user.is_admin ? "/admin" : "/files",
        {
          replace: true,
        }
      );
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <FormCard title="Вход">
      {registered && (
        <div className="success">
          Регистрация завершена. Теперь войдите.
        </div>
      )}

      <form onSubmit={submit}>
        <label>
          Логин
          <input
            value={form.login}
            onChange={(e) =>
              setForm({
                ...form,
                login: e.target.value,
              })
            }
          />
        </label>

        <label>
          Пароль
          <input
            type="password"
            value={form.password}
            onChange={(e) =>
              setForm({
                ...form,
                password: e.target.value,
              })
            }
          />
        </label>

        <FormError error={error} />

        <button className="button" type="submit">
          Войти
        </button>
      </form>
    </FormCard>
  );
}

function FormCard({ title, children }) {
  return (
    <section className="narrow">
      <div className="card">
        <h2>{title}</h2>
        {children}
      </div>
    </section>
  );
}

function Protected({ user, children, admin = false }) {
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (admin && !user.is_admin) {
    return <Navigate to="/files" replace />;
  }

  return children;
}

function FileManager({ user }) {
  const [searchParams] = useSearchParams();

  const selectedUser = user.is_admin
    ? searchParams.get("user_id")
    : null;

  const [data, setData] = useState({
    files: [],
    user: null,
  });

  const [error, setError] = useState("");
  const [comment, setComment] = useState("");
  const [upload, setUpload] = useState(null);
  const [editing, setEditing] = useState(null);
  const [message, setMessage] = useState("");

  async function load() {
    try {
      setData(await api.files(selectedUser));
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, [selectedUser]);

  async function uploadFile(e) {
    e.preventDefault();

    if (!upload) {
      return;
    }

    const fd = new FormData();

    fd.append("file", upload);
    fd.append("comment", comment);

    try {
      await api.upload(fd, selectedUser);

      setUpload(null);
      setComment("");

      e.target.reset();

      setMessage("Файл загружен.");

      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function deleteFile(id) {
    if (!confirm("Удалить файл?")) {
      return;
    }

    try {
      await api.deleteFile(id);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function saveEdit(file) {
    try {
      await api.updateFile(file.id, {
        name: file.original_name,
        comment: file.comment,
      });

      setEditing(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function share(file) {
    try {
      const result = await api.shareFile(file.id);

      /*
       * На HTTPS и в защищённом контексте используем
       * современный Clipboard API.
       */
      if (
        navigator.clipboard &&
        window.isSecureContext
      ) {
        await navigator.clipboard.writeText(
          result.public_url
        );
      } else {
        /*
         * На HTTP, например при открытии сайта
         * по адресу http://178.21.11.59,
         * navigator.clipboard может быть недоступен.
         *
         * Поэтому используем совместимый запасной
         * способ копирования через textarea.
         */
        const textarea = document.createElement("textarea");

        textarea.value = result.public_url;

        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        textarea.style.top = "0";

        document.body.appendChild(textarea);

        textarea.focus();
        textarea.select();

        const copied = document.execCommand("copy");

        document.body.removeChild(textarea);

        if (!copied) {
          throw new Error(
            "Не удалось скопировать ссылку в буфер обмена."
          );
        }
      }

      setMessage(
        "Ссылка скопирована в буфер обмена."
      );
    } catch (err) {
      setError(err.message);
    }
  }

  const storageUser = data.user || user;

  return (
    <section>
      <div className="page-head">
        <div>
          <h2>
            Хранилище: {storageUser.login}
          </h2>

          <p>
            {storageUser.full_name} ·{" "}
            {data.files.length} файлов
          </p>
        </div>
      </div>

      <div className="card upload-card">
        <h3>Загрузить файл</h3>

        <form
          onSubmit={uploadFile}
          className="upload-form"
        >
          <input
            type="file"
            onChange={(e) =>
              setUpload(e.target.files[0])
            }
          />

          <input
            placeholder="Комментарий"
            value={comment}
            onChange={(e) =>
              setComment(e.target.value)
            }
          />

          <button
            className="button"
            type="submit"
          >
            Загрузить
          </button>
        </form>
      </div>

      <FormError error={error} />

      {message && (
        <div className="success">
          {message}
        </div>
      )}

      <div className="card table-wrap">
        <table>
          <thead>
            <tr>
              <th>Имя</th>
              <th>Комментарий</th>
              <th>Размер</th>
              <th>Загружен</th>
              <th>Последнее скачивание</th>
              <th>Операции</th>
            </tr>
          </thead>

          <tbody>
            {data.files.map((file) => (
              <tr key={file.id}>
                <td>
                  {editing?.id === file.id ? (
                    <input
                      value={editing.original_name}
                      onChange={(e) =>
                        setEditing({
                          ...editing,
                          original_name:
                            e.target.value,
                        })
                      }
                    />
                  ) : (
                    file.original_name
                  )}
                </td>

                <td>
                  {editing?.id === file.id ? (
                    <input
                      value={editing.comment}
                      onChange={(e) =>
                        setEditing({
                          ...editing,
                          comment: e.target.value,
                        })
                      }
                    />
                  ) : (
                    file.comment || "—"
                  )}
                </td>

                <td>
                  {formatSize(file.size)}
                </td>

                <td>
                  {formatDate(file.uploaded_at)}
                </td>

                <td>
                  {formatDate(
                    file.last_downloaded_at
                  )}
                </td>

                <td className="row-actions">
                  {editing?.id === file.id ? (
                    <>
                      <button
                        onClick={() =>
                          saveEdit(editing)
                        }
                      >
                        Сохранить
                      </button>

                      <button
                        onClick={() =>
                          setEditing(null)
                        }
                      >
                        Отмена
                      </button>
                    </>
                  ) : (
                    <>
                      <a
                        href={file.download_url}
                      >
                        Скачать
                      </a>

                      <button
                        onClick={() =>
                          setEditing(file)
                        }
                      >
                        Изменить
                      </button>

                      <button
                        onClick={() =>
                          share(file)
                        }
                      >
                        Ссылка
                      </button>

                      <button
                        className="danger"
                        onClick={() =>
                          deleteFile(file.id)
                        }
                      >
                        Удалить
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}

            {!data.files.length && (
              <tr>
                <td
                  colSpan="6"
                  className="empty"
                >
                  Файлов пока нет.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Admin() {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");

  async function load() {
    try {
      setUsers(
        (await api.users()).users
      );
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function toggle(user) {
    try {
      await api.setAdmin(
        user.id,
        !user.is_admin
      );

      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function remove(user) {
    if (
      !confirm(
        `Удалить пользователя ${user.login}?`
      )
    ) {
      return;
    }

    try {
      await api.deleteUser(user.id);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section>
      <h2>Администрирование</h2>

      <p>
        Управление пользователями и их
        файловыми хранилищами.
      </p>

      <FormError error={error} />

      <div className="card table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Логин</th>
              <th>Имя</th>
              <th>Email</th>
              <th>Администратор</th>
              <th>Файлы</th>
              <th>Размер</th>
              <th>Действия</th>
            </tr>
          </thead>

          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.id}</td>
                <td>{u.login}</td>
                <td>{u.full_name}</td>
                <td>{u.email}</td>

                <td>
                  <button
                    onClick={() => toggle(u)}
                  >
                    {u.is_admin ? "Да" : "Нет"}
                  </button>
                </td>

                <td>
                  <Link
                    to={`/files?user_id=${u.id}`}
                  >
                    {u.file_count}
                  </Link>
                </td>

                <td>
                  {formatSize(
                    u.storage_size || 0
                  )}
                </td>

                <td>
                  <button
                    className="danger"
                    onClick={() => remove(u)}
                  >
                    Удалить
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatSize(bytes) {
  if (bytes === 0) {
    return "0 Б";
  }

  const units = [
    "Б",
    "КБ",
    "МБ",
    "ГБ",
    "ТБ",
  ];

  const i = Math.floor(
    Math.log(bytes) / Math.log(1024)
  );

  return `${(
    bytes / Math.pow(1024, i)
  ).toFixed(i ? 1 : 0)} ${units[i]}`;
}

function formatDate(value) {
  return value
    ? new Date(value).toLocaleString("ru-RU")
    : "—";
}

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.me()
      .then((r) => setUser(r.user))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function logout() {
    await api.logout().catch(() => {});

    setUser(null);

    window.location.href = "/";
  }

  if (loading) {
    return (
      <div className="loading">
        Загрузка…
      </div>
    );
  }

  return (
    <Layout
      user={user}
      onLogout={logout}
    >
      <Routes>
        <Route
          path="/"
          element={<Home user={user} />}
        />

        <Route
          path="/register"
          element={
            user ? (
              <Navigate to="/" />
            ) : (
              <Register />
            )
          }
        />

        <Route
          path="/login"
          element={
            user ? (
              <Navigate to="/" />
            ) : (
              <Login onLogin={setUser} />
            )
          }
        />

        <Route
          path="/files"
          element={
            <Protected user={user}>
              <FileManager user={user} />
            </Protected>
          }
        />

        <Route
          path="/admin"
          element={
            <Protected
              user={user}
              admin
            >
              <Admin />
            </Protected>
          }
        />

        <Route
          path="*"
          element={
            <Navigate
              to="/"
              replace
            />
          }
        />
      </Routes>
    </Layout>
  );
}

