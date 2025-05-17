from flask import Flask, render_template, request, Response, send_from_directory
import os
import time # Import time to simulate delay for better visualization
import json # Import json for structured data over SSE

# Import necessary components from utils and agents
# Ensure these modules are available in your Flask project directory
# Assume utils.py and agents.py are correctly set up
from utils import client, call_agent, format_markdown_output, sanitize_filename
from agents import create_agente_buscador, create_agente_planejador, create_agente_redator

app = Flask(__name__)

# Ensure the 'static' directory exists for serving static files like CSS
STATIC_FOLDER = 'static'
if not os.path.exists(STATIC_FOLDER):
    os.makedirs(STATIC_FOLDER)

# --- Setup style.css in static folder ---
# In a real scenario, you'd place your static files directly in the 'static' folder
# For this example, we assume style.css is in the same directory and copy it.
try:
    with open('style.css', 'r') as f_in, open(os.path.join(STATIC_FOLDER, 'style.css'), 'w') as f_out:
        f_out.write(f_in.read())
except FileNotFoundError:
    print("Warning: style.css not found. Please ensure it's in the same directory as app_flask.py")
except Exception as e:
    print(f"Error copying style.css: {e}")

# --- SSE Endpoint ---
# This is the new endpoint that will handle the long-running process and stream updates
@app.route('/process_recipe', methods=['GET'])
def process_recipe_sse():
    ingredients = request.args.get('ingredients') # Get ingredients from query string

    if not ingredients:
        return Response("data: ERROR:Você esqueceu de listar os ingredientes do seu inventário!\n\n", mimetype='text/event-stream')

    if client is None:
         return Response("data: ERROR:Erro na conexão com os grandes mestres alquimistas (Google API Key). Verifique as configurações.\n\n", mimetype='text/event-stream')

    def generate_events():
        try:
            # Send initial status message
            yield "data: STATUS:INICIADO:Forjando receita com: {}\n\n".format(ingredients)
            time.sleep(1) # Simulate setup time

            # Initialize agents (can do this outside the generator if they are reused)
            # If agents need context per request, keep them inside
            try:
                 buscador_agent = create_agente_buscador()
                 planejador_agent = create_agente_planejador()
                 redator_agent = create_agente_redator()
            except Exception as e:
                 yield f"data: ERROR:Falha ao inicializar agentes: {e}\n\n"
                 return # Stop processing if agents fail to init


            # Step 1: Search for recipes
            yield "data: STATUS:RUNNING:1:Passo 1: Vasculhando tomos antigos por receitas compatíveis...\n\n"
            time.sleep(2) # Simulate work
            searched_recipes = call_agent(buscador_agent, f"Tópico: {ingredients} \n")
            if "Error during agent run" in searched_recipes:
                raise Exception(searched_recipes.split("Error during agent run: ", 1)[-1]) # Extract message
            yield "data: STATUS:COMPLETE:1:Passo 1 Concluído: Pergaminhos encontrados!\n\n"
            time.sleep(1) # Simulate transition time

            # Step 2: Plan the recipe
            yield "data: STATUS:RUNNING:2:Passo 2: Decifrando e planejando a receita principal...\n\n"
            time.sleep(2) # Simulate work
            recipe_plan = call_agent(planejador_agent, f"Tópico:{ingredients}\nLançamentos buscados: {searched_recipes}")
            if "Error during agent run" in recipe_plan:
                raise Exception(recipe_plan.split("Error during agent run: ", 1)[-1]) # Extract message
            yield "data: STATUS:COMPLETE:2:Passo 2 Concluído: Plano da receita traçado!\n\n"
            time.sleep(1) # Simulate transition time

            # Step 3: Generate the recipe post content
            yield "data: STATUS:RUNNING:3:Passo 3: Transcrevendo o encantamento... digo, o tutorial da receita...\n\n"
            time.sleep(3) # Simulate work
            recipe_post_content = call_agent(redator_agent, f"Tópico: {ingredients}\nPlano de post: {recipe_plan}")
            if "Error during agent run" in recipe_post_content:
                raise Exception(recipe_post_content.split("Error during agent run: ", 1)[-1]) # Extract message
            yield "data: STATUS:COMPLETE:3:Passo 3 Concluído: A fórmula mágica está pronta!\n\n"
            time.sleep(1) # Simulate transition time

            # Send the final recipe content
            # It's better to send the content as a single final event
            # You might need to encode it if it contains special characters or newlines
            final_recipe_data = {
                "content": format_markdown_output(recipe_post_content),
                "filename": sanitize_filename(recipe_post_content)
            }
            yield "data: RECIPE_COMPLETE:{}\n\n".format(json.dumps(final_recipe_data))
            yield "data: STATUS:FINALIZADO:Receita gerada com sucesso!\n\n"


        except Exception as e:
            error_str = f"Um feitiço deu errado durante a conjuração da receita: {e}"
            yield f"data: ERROR:{error_str}\n\n"

    # Return the Response object configured for SSE
    return Response(generate_events(), mimetype='text/event-stream')


# --- Main Render Route ---
@app.route('/', methods=['GET']) # Only GET needed now, POST handled by JS
def index():
    # This route just renders the initial page template
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(STATIC_FOLDER, filename)


if __name__ == '__main__':
    # In a real deployment, use a production-ready server like Gunicorn or uWSGI
    # and potentially a background task queue for long processes
    app.run(debug=True) # debug=True enables auto-reloading and detailed errors