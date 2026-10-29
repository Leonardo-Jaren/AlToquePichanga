import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'
import { instalarProteccion } from './router/proteccion'
import { instalarManejoSesion } from '@/modules/autenticacion/services/manejoSesion'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
instalarProteccion(router, pinia)
instalarManejoSesion(router, pinia)
app.use(router)

app.mount('#app')
