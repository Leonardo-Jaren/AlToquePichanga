# Comprobación física de cámara para asistencia

## Requisitos antes de probar

- Abrir la app por `https://` con un certificado válido y confiable. `localhost` sirve para
  desarrollo en el mismo dispositivo; una URL HTTP con la IP local de otra máquina no es un
  contexto seguro.
- Iniciar sesión con una cuenta cajero asignada a la sede del QR y usar una reserva demo
  confirmada que esté dentro de su horario.
- La lectura requiere `navigator.mediaDevices.getUserMedia` y `BarcodeDetector` con el formato
  `qr_code`. La cámara requiere contexto seguro y permiso del usuario; `BarcodeDetector` tiene
  soporte limitado y varía entre navegadores. En ausencia de compatibilidad, usar el código
  manual de la reserva.

Referencias: [Barcode Detection API](https://developer.mozilla.org/en-US/docs/Web/API/Barcode_Detection_API),
[getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia) y
[contextos seguros](https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Secure_Contexts).

## Android (Chrome u otro navegador compatible)

1. Abre el sitio HTTPS y permite el acceso a la cámara cuando el navegador lo solicite. Si no
   aparece la solicitud, revisa el permiso de cámara del sitio en la configuración del
   navegador y el permiso de cámara de la app en Android.
2. En **Reservas → Validar ingreso**, pulsa **Abrir cámara** y apunta la cámara trasera al QR.
   Mantén el código enfocado, iluminado y dentro del recuadro de vista previa.
3. Confirma los datos de sede, cancha, fecha y saldo. Pulsa **Registrar ingreso** una sola vez.
   Escanea de nuevo el mismo QR: debe indicar que el ingreso ya fue registrado y no ofrecer un
   segundo registro.
4. Cancela otra reserva demo confirmada y comprueba que su QR no se valide. No uses reservas,
   cuentas ni comprobantes de clientes reales para la comprobación.
5. Repite después de denegar el permiso, retirar el permiso desde ajustes y ocupar la cámara
   con otra app. La interfaz debe mostrar una salida clara y permitir ingresar el código
   manualmente.

## Otros dispositivos compatibles

En una computadora, tablet u otro teléfono, comprueba que el navegador anuncie `qr_code` en
`BarcodeDetector.getSupportedFormats()` y que permita `getUserMedia`. Repite el flujo de
permiso, escaneo, doble escaneo e ingreso manual. No se da por compatible a un navegador o
modelo por su nombre solamente: las dos APIs y sus formatos deben estar disponibles en esa
instalación.

## Estado de la comprobación

Playwright valida el flujo de la interfaz y las respuestas del servidor con una cámara
simulada; no valida sensores, enfoque, permisos del sistema operativo ni iluminación. No se
dispuso de un dispositivo físico en esta ejecución. La prueba física en Android y otros
dispositivos compatibles queda **PENDIENTE**.
