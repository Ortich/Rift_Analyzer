# Riftbound Analyzer

Riftbound Analyzer es un motor de análisis y simulación diseñado para optimizar y evaluar matemáticamente mazos del juego de cartas **Riftbound**. Partiendo de una lista de cartas en texto plano, el sistema clasifica las cartas, simula miles de partidas para calcular la consistencia y arroja una puntuación competitiva (Power Level) junto con un análisis táctico interpretado por Inteligencia Artificial.

## Arquitectura de 4 Fases

El sistema está dividido en cuatro capas secuenciales, orquestadas de forma automática:

### Fase 1: Parseo y Heurística (`scripts/analyze_deck.py`)
El motor lee el archivo `.txt` del mazo y cruza la información con la base de datos local de Riftcodex. 
- Valida las reglas de construcción (40 cartas exactas, máximo 3 copias, máximo 2 dominios).
- Separa las cartas en slots especiales: **Champion** y **Legend** (que van en su propia zona y no cuentan para el límite de 40 cartas).
- Extrae la curva de energía, el coste de quemado (Burn Cost / Power) y el poder de combate (Might).
- Genera un archivo estático: `data/db/parsed_deck.json`.

### Fase 2: Simulación de Mazos de Viktor (`core/simulator.py`)
Utiliza los costes extraídos en la Fase 1 para simular **partidas completas (Al Mejor de 3)** contra 3 bots abstractos (Aggro, Control, Midrange).
- **Reglas de Riftbound integradas**:
  - Batallas multicarril: El *Might* generado se divide en carriles, y sumar la mayoría en un carril otorga 1 VP. El primero en llegar a 8 VP gana.
  - Mano inicial de 4 cartas y Robo de 2 Energías por turno.
  - El Jugador 1 no roba carta en el Turno 1 (se alterna quién empieza en cada ronda del Bo3).
  - Algoritmo de Mulligan inteligente.
  - Interacción: Los Hechizos/Spells restan Might directamente al oponente.

### Fase 3: Puntuación y Bracketing (`core/score.py`)
Toma los resultados de la simulación y genera métricas competitivas:
- **Speed, Consistency, Interaction, Closing Power**: Sub-puntuaciones matemáticas.
- **Power Level**: Puntuación global del mazo sobre 10.
- **Tier Competitivo**: Desde Tier 4 (Casual) hasta Tier 1 (Optimized/Competitive).
- Genera el reporte final: `data/db/final_report.json`.

### Fase 4: Interpretación Experta por IA (`.agents/skills/riftbound-analyzer/SKILL.md`)
Una "Skill" preconfigurada para que un Agente IA lea los resultados matemáticos (`final_report.json` y `parsed_deck.json`). La IA actúa como un "Juez Experto", detectando problemas (Closing Gap, falta de interacción, curva muy alta) y sugiriendo cambios específicos de cartas (IN/OUT) para optimizar el mazo.

---

## Cómo Ejecutar la Aplicación

Toda la ejecución matemática (Fases 1 a 3) se realiza con un solo comando utilizando el orquestador principal.

### 1. Ejecutar el Pipeline de Análisis
En tu terminal, situado en la raíz del proyecto, ejecuta el orquestador pasándole la ruta del mazo que quieres analizar. Por ejemplo, con el mazo de muestra:

```bash
python scripts/analyze_pipeline.py data/decks/sample.txt
```

### 2. Revisar los Resultados
El script imprimirá por consola el resumen del análisis, el porcentaje de consistencia, el turno medio de plan, y la puntuación final (Power Level y Tier). Además, se generarán y actualizarán los artefactos internos en la carpeta `data/db/`.

### 3. Pedir el Análisis a la IA (Fase 4)
Una vez finalizado el comando anterior, simplemente pide a tu Agente IA en el chat que analice el mazo. La IA utilizará su contexto y la Skill cargada (`riftbound-analyzer`) para interpretar los JSON resultantes y darte sus sugerencias de mejora táctica.

---

## Notas de Diseño del Motor

- **Might vs Power**: En la API de Riftbound, `might` representa el poder de combate (ganas si tu Might es superior al del rival), mientras que `power` se utiliza internamente en nuestro simulador como el **Energy Burn Cost** (el coste adicional que te obliga a quemar una energía máxima al jugar la carta).
- **Zonas Especiales**: El Champion y la Legend del mazo se excluyen automáticamente de los cálculos de la curva de energía y del tamaño de mazo de 40 cartas para no alterar las simulaciones de robo en los primeros turnos.
