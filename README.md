# 📍 Rastreador de teléfonos

Servidor sencillo para ver la ubicación de tus teléfonos Android en un mapa,
desde cualquier navegador (Chrome, por ejemplo). Cada teléfono envía su
ubicación con la app gratuita **GPSLogger** y aquí se muestra en un tablero.

> ⚠️ **Nota de privacidad:** el tablero es público para quien conozca la URL.
> Es tu despliegue personal, pero no publiques la dirección. La recepción de
> ubicaciones (`/api/report`) está protegida con un token secreto.

---

## 1. Probar en tu computadora

```bash
cd ~/workspace/phone-tracker
pip install -r requirements.txt
SECRET_TOKEN=miclave python app.py
```

Abre http://localhost:5000 en Chrome. Simula un reporte:

```bash
curl "http://localhost:5000/api/report?token=miclave&device=telefono1&lat=19.4326&lon=-99.1332&batt=87&acc=12"
curl http://localhost:5000/api/positions
```

## 2. Configurar GPSLogger en cada teléfono

1. Instala **GPSLogger for Android** (de F-Droid o desde
   https://gpslogger.app — no está en Google Play).
2. En la app: **Ajustes → Custom URL** y activa **Log to custom URL**.
3. En **URL** pega (cambia `TU-SERVIDOR`, `TU_TOKEN` y el nombre del teléfono):

   ```
   https://TU-SERVIDOR/api/report?token=TU_TOKEN&device=telefono1&lat=%LAT&lon=%LON&batt=%BATT&acc=%ACC&alt=%ALT&spd=%SPD&time=%TIME
   ```

   > **Importante:** pon un `device=` distinto en cada teléfono
   > (`telefono1`, `telefono2`, `trabajo`…) — ese nombre aparece en el mapa.

4. **Método HTTP:** puedes dejarlo en **GET** (funciona con la URL de arriba).
5. En **Ajustes → Logging details** elige cada cuánto quieres un punto
   (por ejemplo, cada 5 minutos o cada 100 metros).
6. Pulsa **Start logging**. Si el teléfono se queda sin internet, GPSLogger
   guarda los puntos y los envía cuando vuelve la conexión.

### Placeholders de GPSLogger que usamos

| Placeholder | Significado                 |
|-------------|-----------------------------|
| `%LAT`      | Latitud                     |
| `%LON`      | Longitud                    |
| `%BATT`     | Batería (%)                 |
| `%ACC`      | Precisión (metros)          |
| `%ALT`      | Altitud                     |
| `%SPD`      | Velocidad (m/s)             |
| `%TIME`     | Hora del punto              |
| `%TIMESTAMP`| Marca de tiempo (epoch)     |
| `%ISCHARGING`| 1 si está cargando         |
| `%DIR`      | Dirección/brújula           |

El servidor también acepta reportes en JSON por POST si prefieres ese formato.

## 3. Publicarlo en internet (gratis)

Necesitas que el servidor tenga una URL pública para que los teléfonos
puedan enviar su ubicación. Opciones gratuitas:

**Render** (el más sencillo):
1. Sube esta carpeta a un repositorio de GitHub.
2. En https://render.com crea un **Web Service** apuntando al repositorio.
3. Render detecta el `Dockerfile` automáticamente.
4. En *Environment*, agrega la variable `SECRET_TOKEN` con tu clave.
5. Te dará una URL como `https://rastreador.onrender.com` — esa es tu `TU-SERVIDOR`.

**Railway / Fly.io:** proceso parecido (Dockerfile incluido); configura la
variable `SECRET_TOKEN` y obtén la URL pública.

## 4. Ver el mapa

Abre en Chrome la URL de tu servidor (o http://localhost:5000 en pruebas).
El tablero muestra un marcador por teléfono con su nombre, última
actualización y batería, y se refresca solo cada 30 segundos.

## API (resumen)

- `GET/POST /api/report?token=…&device=…&lat=…&lon=…` → registra una posición.
- `GET /api/positions` → última posición de cada teléfono (JSON).
- `GET /api/history/<device>` → últimos 50 puntos de un teléfono.
- `DELETE /api/devices/<device>` → elimina un teléfono del tablero.
- `GET /health` → estado del servidor.

Los datos se guardan en `data/positions.json` (sin base de datos externa).
