import { onUnmounted, ref } from 'vue'
import { io, Socket } from 'socket.io-client'

let _socket: Socket | null = null

function getSocket(): Socket {
  if (!_socket) {
    _socket = io('/', {
      auth: { token: localStorage.getItem('token') ?? '' },
      transports: ['websocket'],
    })
  }
  return _socket
}

export function useTaskSocket(taskId: string, onLine: (line: string) => void, onStatus: (status: string) => void) {
  const socket = getSocket()

  socket.emit('subscribe_task', { task_id: taskId })
  socket.on('task_output', (data: { task_id: string; line: string }) => {
    if (data.task_id === taskId) onLine(data.line)
  })
  socket.on('task_status', (data: { task_id: string; status: string }) => {
    if (data.task_id === taskId) onStatus(data.status)
  })

  onUnmounted(() => {
    socket.emit('unsubscribe_task', { task_id: taskId })
    socket.off('task_output')
    socket.off('task_status')
  })
}
