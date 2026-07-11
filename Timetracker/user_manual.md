# Manual de Usuario: TimeTracker - Gestión y Análisis de Tiempo

¡Bienvenido al manual de usuario de su aplicación TimeTracker! Esta herramienta ha sido diseñada para ayudarle a registrar sus actividades diarias, gestionar el tiempo dedicado a diferentes tareas y obtener una visión clara del uso de su tiempo a través de un dashboard interactivo.

## 1. Cómo Iniciar la Aplicación

Para comenzar a utilizar TimeTracker, siga estos sencillos pasos:

1.  **Abra su terminal** o línea de comandos.
2.  **Navegue hasta la carpeta principal** de su proyecto TimeTracker. Por ejemplo, si está en `C:\Users\ferca	imetracker`, asegúrese de que su terminal esté en esa ubicación.
3.  **Ejecute el siguiente comando:**
    ```bash
    python run.py
    ```
4.  **Acceso al Navegador:** Una vez ejecutado el comando, la aplicación se abrirá automáticamente en su navegador web predeterminado. Si no es así, puede acceder manualmente ingresando la siguiente dirección en la barra de direcciones de su navegador: `http://localhost:8501`.

La aplicación se ejecutará en segundo plano. Para detenerla, simplemente cierre la terminal donde la inició o presione `Ctrl+C` en esa terminal.

## 2. Características Principales y Funcionamiento

La aplicación TimeTracker consta de dos secciones principales, accesibles a través de la barra lateral en su navegador:

### 2.1. TimeTracker (Página Principal)

Esta es la sección principal para el registro y gestión de sus tareas.

*   **Formulario de Entrada de Tareas:**
    *   En la parte superior de la página, encontrará un formulario para crear nuevas tareas.
    *   Rellene los campos: `Cliente`, `Proyecto`, `Descripción`, `Etiquetas` (puede usar palabras clave separadas por comas como "servicio, diseño, urgente"), `Facturable` (marque si la tarea es facturable) y `Notas`.
    *   Haga clic en "Crear Tarea" para añadirla a su lista.

*   **Control de Tiempo (Temporizador):**
    *   En la barra lateral izquierda, verá un widget de "Control de Tiempo".
    *   **Iniciar:** Seleccione una tarea de la lista desplegable y haga clic en "Iniciar Tarea". El temporizador comenzará a contar.
    *   **Detener:** Cuando termine de trabajar en la tarea, haga clic en "Detener Tarea". El tiempo registrado se guardará automáticamente.

*   **Lista de Tareas Registradas:**
    *   Debajo del formulario de entrada, se muestra una tabla con todas sus tareas.
    *   Cada fila muestra el `ID`, `Cliente`, `Proyecto`, `Descripción`, el `Tiempo Total` dedicado a esa tarea (en minutos), si es `Facturable` y `Acciones`.

*   **Edición de Tareas:**
    *   Junto a cada tarea en la lista, encontrará un botón "✏️ Editar".
    *   Al hacer clic en "Editar", la vista cambiará a un formulario de edición donde podrá modificar los detalles de la tarea.
    *   Guarde los cambios o cancele la edición.

*   **Eliminación de Tareas:**
    *   Junto a cada tarea en la lista, también encontrará un botón "🗑️ Borrar".
    *   Al hacer clic en "Borrar", la tarea y todas sus entradas de tiempo asociadas serán eliminadas permanentemente.

### 2.2. Dashboard (Página de Análisis)

El Dashboard le proporciona una visión analítica del tiempo registrado. Para acceder a él, seleccione "Dashboard" en la barra lateral.

*   **Horas Totales:**
    *   **Por Día:** Un gráfico de barras muestra la cantidad total de horas trabajadas cada día.
    *   **Por Semana:** Otro gráfico de barras presenta el total de horas acumuladas por semana, ofreciendo una perspectiva más amplia.

*   **Distribución por Cliente:**
    *   Un gráfico de tarta (pie chart) visualiza cómo se distribuye su tiempo entre los diferentes clientes. Cada porción del pastel representa un cliente y su proporción de horas trabajadas.

*   **Ratio Servicio vs. Desarrollo de Producto:**
    *   Esta sección analiza su dedicación entre tareas de "servicio" y de "desarrollo de producto".
    *   **Funcionamiento:** Para que esta métrica funcione correctamente, es crucial que al crear o editar tareas, utilice las etiquetas (`tags`) de manera consistente. Por ejemplo, incluya la palabra "servicio" para tareas relacionadas con clientes o soporte, y "producto" para aquellas enfocadas en el desarrollo o mejora de productos internos.
    *   Un gráfico de barras muestra las horas dedicadas a cada categoría, y se presenta un ratio numérico (Horas Producto / Horas Servicio) que indica su enfoque principal.

## 3. Consideraciones Adicionales

*   **Persistencia de Datos:** Todos sus datos (tareas y entradas de tiempo) se guardan automáticamente en una base de datos local SQLite (`timetracker.db`), asegurando que su información no se pierda al cerrar la aplicación.
*   **Métrica de Eficiencia (Futura):** La métrica de "eficiencia: tiempo real vs tiempo estimado" no está implementada en esta versión, ya que la base de datos actual no almacena el tiempo estimado para las tareas. Esto podría ser una mejora futura si lo considera necesario.

Esperamos que este manual le sea de gran utilidad para aprovechar al máximo su TimeTracker. ¡Gracias por utilizar nuestra solución!