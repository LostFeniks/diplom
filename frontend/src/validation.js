export const loginRegex = /^[A-Za-z][A-Za-z0-9]{3,19}$/;
export const passwordRegex = /^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{6,}$/;
export const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateRegistration(form) {
  const errors = {};
  if (!loginRegex.test(form.login)) {
    errors.login = "Логин: латинские буквы и цифры, первый символ — буква, 4–20 символов.";
  }
  if (!form.full_name.trim()) errors.full_name = "Введите полное имя.";
  if (!emailRegex.test(form.email)) errors.email = "Введите корректный email.";
  if (!passwordRegex.test(form.password)) {
    errors.password = "Минимум 6 символов: заглавная буква, цифра и специальный символ.";
  }
  return errors;
}
