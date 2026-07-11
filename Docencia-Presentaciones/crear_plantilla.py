from pptx import Presentation
from pptx.dml.color import RGBColor

def definir_plantilla_cnnia(output_filename):
    """Crea y guarda una plantilla de presentación con la paleta de colores de CNNIA."""
    prs = Presentation()
    master = prs.slide_master

    # --- Definir Paleta de Colores CNNIA ---
    COLOR_FONDO = "0d1b2a"      # Azul marino oscuro
    COLOR_TEXTO = "E0E1DD"      # Gris claro / casi blanco
    COLOR_ACENTO_1 = "00A6A6"   # Verde azulado (Teal)
    COLOR_ACENTO_2 = "415a77"   # Gris pizarra
    COLOR_ACENTO_3 = "778da9"   # Gris pizarra claro
    COLOR_ACENTO_4 = "1b263b"   # Azul marino más oscuro

    # --- Aplicar Fondo a la Diapositiva Maestra ---
    background = master.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor.from_string(COLOR_FONDO)

    # --- Acceder al Esquema de Colores a través del Tema ---
    theme = master.theme
    color_scheme = theme.color_scheme

    # --- Modificar los colores del tema ---
    color_scheme.dark_1.rgb = RGBColor.from_string(COLOR_FONDO)
    color_scheme.light_1.rgb = RGBColor.from_string(COLOR_TEXTO)
    color_scheme.accent_1.rgb = RGBColor.from_string(COLOR_ACENTO_1)
    color_scheme.accent_2.rgb = RGBColor.from_string(COLOR_ACENTO_2)
    color_scheme.accent_3.rgb = RGBColor.from_string(COLOR_ACENTO_3)
    color_scheme.accent_4.rgb = RGBColor.from_string(COLOR_ACENTO_4)

    # --- Modificar Estilos de Texto Maestros ---
    # Título
    title_style = master.title_style
    title_style.font.name = 'Calibri Light'
    title_style.font.color.rgb = RGBColor.from_string(COLOR_ACENTO_1) # Usar el Teal para títulos

    # Cuerpo
    body_style = master.body_style
    body_style.font.name = 'Calibri'
    body_style.font.color.rgb = RGBColor.from_string(COLOR_TEXTO) # Texto principal claro

    print(f"🎨 Plantilla con tema CNNIA definida. Guardando en '{output_filename}'...")
    prs.save(output_filename)
    print(f"✅ Plantilla '{output_filename}' guardada con éxito.")

if __name__ == "__main__":
    definir_plantilla_cnnia("plantilla_cnnia.pptx")
