import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image
import io

# --- CONFIGURACIÓN ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ ERROR: No se encontró GOOGLE_API_KEY en el archivo .env")
    sys.exit(1)

def generar_visual_cnnia(prompt_usuario, nombre_archivo):
    """Genera una imagen usando Imagen 4 (la más reciente disponible) con estilo CNNIA."""
    client = genai.Client(api_key=api_key)
    
    # Estilo base solicitado por el usuario
    estilo_cnnia = "Estilo minimalista, tecnológico. Una red de nodos conectando eslabones de calidad. Paleta de colores: Azul oscuro (CNNIA) y gris. Fondo limpio."
    prompt_final = f"{estilo_cnnia} {prompt_usuario}"
    
    print(f"🎨 Generando visual con Imagen: '{prompt_final}'...")
    
    try:
        # Usamos imagen-4.0-generate-001 que estaba en la lista de modelos.
        response = client.models.generate_images(
            model='imagen-4.0-generate-001',
            prompt=prompt_final,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type='image/png'
            )
        )
        
        for i, generated_image in enumerate(response.generated_images):
            image = Image.open(io.BytesIO(generated_image.image.image_bytes))
            
            output_dir = Path("Salidas_Generadas")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"{nombre_archivo}.png"
            
            image.save(output_path)
            print(f"✅ Visual guardada exitosamente en: {output_path}")
            return str(output_path)

    except Exception as e:
        print(f"❌ Error al generar la imagen: {e}")
        return None

if __name__ == "__main__":
    prompt = "Una red de nodos tecnológicos conectando eslabones de calidad, estilo minimalista, colores azul CNNIA y gris."
    generar_visual_cnnia(prompt, "Visual_Red_Calidad_CNNIA")
