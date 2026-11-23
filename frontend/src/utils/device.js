/** 浏览器设备标识：同一浏览器多标签页共用一个设备 ID（在线状态的多端语义）。 */
export function getDeviceId() {
  const key = 'sl_chat_device'
  let id = localStorage.getItem(key)
  if (!id) {
    id = 'd' + Math.random().toString(36).slice(2, 10)
    localStorage.setItem(key, id)
  }
  return id
}
