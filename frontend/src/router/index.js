import { createRouter, createWebHistory } from 'vue-router'
import InicioView from '@/modules/inicio/views/InicioView.vue'

const routes = [
  { path: '/google-retorno', component: () => import('@/modules/autenticacion/views/GoogleRetornoView.vue') },
  {
    path: '/',
    name: 'inicio',
    component: InicioView,
  },
  { path: '/canchas-publicas', name: 'canchas-publicas', component: () => import('@/modules/calendario/views/CanchasPublicasView.vue') },
  { path: '/mis-reservas', name: 'mis-reservas', component: () => import('@/modules/reservas/views/MisReservasView.vue'), meta: { autenticado: true } },
  { path: '/mis-reservas/:codigo/pago', name: 'pago-reserva', component: () => import('@/modules/pagos/views/PagoReservaView.vue'), meta: { autenticado: true } },
  { path: '/ingresar', name: 'ingresar', component: () => import('@/modules/autenticacion/views/IngresarView.vue'), meta: { invitado: true } },
  { path: '/registro', component: () => import('@/modules/autenticacion/views/RegistroView.vue'), meta: { invitado: true } },
  { path: '/recuperar', component: () => import('@/modules/autenticacion/views/RecuperarView.vue') },
  { path: '/restablecer', component: () => import('@/modules/autenticacion/views/EnlaceView.vue') },
  { path: '/verificar-correo', name: 'verificar-correo', component: () => import('@/modules/autenticacion/views/EnlaceView.vue') },
  { path: '/perfil', component: () => import('@/modules/autenticacion/views/PerfilView.vue'), meta: { autenticado: true } },
  { path: '/panel/jugador', component: () => import('@/modules/autenticacion/views/PanelView.vue'), meta: { autenticado: true, rol: 'jugador' } },
  { path: '/panel/dueno', component: () => import('@/modules/empresas/views/PanelEmpresaView.vue'), meta: { autenticado: true, rol: 'dueno' } },
  { path: '/panel/administrador_sede', component: () => import('@/modules/administracion/views/PanelSedeView.vue'), meta: { autenticado: true, rol: 'administrador_sede' } },
  { path: '/panel/cajero', component: () => import('@/modules/administracion/views/PanelCajeroView.vue'), meta: { autenticado: true, rol: 'cajero' } },
  { path: '/panel/plataforma', component: () => import('@/modules/administracion/views/PanelPlataformaView.vue'), meta: { autenticado: true, rol: 'plataforma' } },
  { path: '/sin-permiso', name: 'sin-permiso', component: () => import('@/modules/autenticacion/views/AccesoView.vue') },
  { path: '/sesion-no-disponible', name: 'sesion-no-disponible', component: () => import('@/modules/autenticacion/views/AccesoView.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router
