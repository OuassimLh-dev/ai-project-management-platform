const key = "project-workspace-token";
const listeners = new Set<() => void>();
export const getToken = () => sessionStorage.getItem(key);
export const setToken = (token: string) => sessionStorage.setItem(key, token);
export function clearToken() {
  sessionStorage.removeItem(key);
  listeners.forEach((listener) => listener());
}
export function onTokenCleared(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
