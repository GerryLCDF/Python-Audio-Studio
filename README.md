# 🎙️ Python Audio Studio - Pro Edition

Una aplicación de escritorio potente y ligera diseñada para la grabación y edición de voz profesional. Ideal para locutores y creadores de contenido que necesitan un flujo de trabajo ágil con guion integrado.

## ✨ Características Principales

* **Grabación de Alta Fidelidad:** Captura audio en formato nativo WAV (`44100Hz`, `16-bit`).
* **Selector de Dispositivo:** Selección dinámica de micrófonos y entradas de audio.
* **Vúmetro Estilo OBS:** Indicador visual de intensidad para monitorear niveles de entrada.
* **Visor de Onda Dinámico (Waveform):** Visualización de la pista con soporte para:
    * **Zoom Inteligente:** `Ctrl + Rueda del ratón` para ampliar o reducir la onda.
    * **Desplazamiento Lateral:** Navegación por la pista mediante scroll.
    * **Auto-Scroll:** El visor sigue la grabación en tiempo real sin comprimir la imagen.
* **Edición Precisa:** Selección de fragmentos con el mouse para:
    * Reproducir únicamente la selección (pre-escucha).
    * Cortar y eliminar errores de forma instantánea.
* **Teleprompter Integrado:** Lector de archivos **PDF** y **Word (.docx)** con scroll independiente.
* **Interfaz Dark Mode:** Diseño de alto contraste optimizado para sesiones largas (1150x750px).

---

## 🛠️ Requisitos del Sistema

### 1. Pre-requisitos
* **Python:** 3.8 o superior.
* **Acceso a Micrófono:** Permisos habilitados en el sistema operativo.

### 2. Librerías Necesarias
Instala las dependencias ejecutando el siguiente comando en tu terminal:

```bash
pip install pyaudio numpy PyPDF2 python-docx
