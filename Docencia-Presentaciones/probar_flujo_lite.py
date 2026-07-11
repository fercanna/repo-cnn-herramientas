import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
import re

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

def probar_flujo_logico(ruta_guion):
    client = genai.Client(api_key=api_key)
    
    # Leer el guion
    texto = Path(ruta_guion).read_text(encoding="utf-8")
    # Separar por diapositivas (formato DIAPOSITIVA N:)
    bloques = re.split(r"DIAPOSITIVA \d+:", texto)[1:]
    
    print(f"--- PRUEBA DE FLUJO LÓGICO (Modelo: gemini-3.1-flash-lite-preview) ---")
    print(f"Procesando: {ruta_guion}\n")

    for i, bloque in enumerate(bloques[:3], 1): # Probamos con las primeras 3
        # Extraer el visual sugerido
        visual_match = re.search(r"\[Visual\]:(.*)", bloque, re.DOTALL)
        visual_original = visual_match.group(1).strip().split('\n')[0] if visual_match else "Sin visual"
        
        # Prompt para Gemini 3.1 para optimizar el prompt de imagen
        instruccion = (
            f"Actúa como un experto en prompts para IA de generación de imágenes (Imagen 3/4). "
            f"Toma la siguiente idea visual en español: '{visual_original}'. "
            f"Crea un prompt en inglés que sea: profesional, minimalista, tecnológico, estilo red de nodos, "
            f"con paleta de colores azul oscuro (CNNIA) y gris. "
            f"Responde ÚNICAMENTE con el prompt en inglés."
        )
        
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite-preview',
            contents=instruccion
        )
        
        prompt_ingles = response.text.strip()
        
        print(f"Slide {i}:")
        print(f"  > Original: {visual_original}")
        print(f"  > AI Prompt (English): {prompt_ingles}\n")

if __name__ == "__main__":
    guion = "Salidas_Generadas/Guio_Presentación Gestión de Riesgos_ANOA.txt"
    probar_flujo_logico(guion)
