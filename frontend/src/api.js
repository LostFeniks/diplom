async function request(url, options = {}) {
  const headers = new Headers(options.headers || {});
  const isFormData = options.body instanceof FormData;

  if (!isFormData && options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(url, {
    credentials: "include",
    ...options,
    headers,
  });

  const contentType = response.headers.get("content-type") || "";

  let data = null;

  if (contentType.includes("application/json")) {
    data = await response.json();
  }

  if (!response.ok) {
    let message = `Ошибка HTTP ${response.status}`;

    if (data?.error) {
      message = data.error;
    } else if (data?.errors) {
      const errors = Object.values(data.errors)
        .flat()
        .filter(Boolean);

      if (errors.length > 0) {
        message = errors.join(" ");
      }
    } else if (typeof data === "string") {
      message = data;
    }

    throw new Error(message);
  }

  return data;
}

export const api = {
  // Аутентификация
  me: () => request("/api/auth/me/"),

  register: (body) =>
    request("/api/auth/register/", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  login: (body) =>
    request("/api/auth/login/", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  logout: () =>
    request("/api/auth/logout/", {
      method: "POST",
    }),

  // Администрирование пользователей
  users: () =>
    request("/api/users/"),

  deleteUser: (id) =>
    request(`/api/users/${id}/`, {
      method: "DELETE",
    }),

  setAdmin: (id, isAdmin) =>
    request(`/api/users/${id}/admin/`, {
      method: "PATCH",
      body: JSON.stringify({
        is_admin: isAdmin,
      }),
    }),

  // Файлы
  files: (userId = null) => {
    const query = userId !== null && userId !== undefined
      ? `?user_id=${encodeURIComponent(userId)}`
      : "";

    return request(`/api/files/${query}`);
  },

  upload: (formData, userId = null) => {
    const query = userId !== null && userId !== undefined
      ? `?user_id=${encodeURIComponent(userId)}`
      : "";

    return request(`/api/files/upload/${query}`, {
      method: "POST",
      body: formData,
    });
  },

  updateFile: (id, body) =>
    request(`/api/files/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  deleteFile: (id) =>
    request(`/api/files/${id}/`, {
      method: "DELETE",
    }),

  shareFile: (id) =>
    request(`/api/files/${id}/share/`, {
      method: "POST",
    }),

  downloadFile: (id) =>
    `/api/files/${id}/download/`,
};