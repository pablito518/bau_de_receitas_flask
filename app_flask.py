from flask import Flask, render_template, request, send_from_directory
import os
# Import necessary components from utils and agents
# Ensure these modules are available in your Flask project directory
from utils import client, call_agent, format_markdown_output, sanitize_filename, render_markdown_to_html
from agents import create_agente_buscador, create_agente_planejador, create_agente_redator

app = Flask(__name__)

# Ensure the 'static' directory exists for serving static files like CSS
if not os.path.exists('static'):
    os.makedirs('static')

# Copy the style.css to the static folder if it's not already there
# In a real scenario, you'd place your static files directly in the 'static' folder
# For this example, we assume style.css is in the same directory and copy it.
try:
    with open('style.css', 'r') as f_in, open('static/style.css', 'w') as f_out:
        f_out.write(f_in.read())
except FileNotFoundError:
    print("Warning: style.css not found. Please ensure it's in the same directory as app_flask.py")
except Exception as e:
    print(f"Error copying style.css: {e}")


@app.route('/', methods=['GET', 'POST'])
def index():
    recipe_post_content = None
    error_message = None
    ingredients = ""
    download_filename = "untitled_recipe.txt" # Default filename
    
    if request.method == 'POST':
        ingredients = request.form.get('ingredients')

        if not ingredients:
            error_message = "Você esqueceu de listar os ingredientes do seu inventário!"
        elif client is None:
             error_message = "Erro na conexão com os grandes mestres alquimistas (Google API Key). Verifique as configurações."
        else:
            try:
                # Initialize agents
                buscador_agent = create_agente_buscador()
                planejador_agent = create_agente_planejador()
                redator_agent = create_agente_redator()

                # Step 1: Search for recipes
                searched_recipes = call_agent(buscador_agent, f"Tópico: {ingredients} \n")
                if "Error during agent run" in searched_recipes:
                    raise Exception(searched_recipes)

                # Step 2: Plan the recipe
                recipe_plan = call_agent(planejador_agent, f"Tópico:{ingredients}\nLançamentos buscados: {searched_recipes}")
                if "Error during agent run" in recipe_plan:
                    raise Exception(recipe_plan)

                # Step 3: Generate the recipe post content
                recipe_post_content = call_agent(redator_agent, f"Tópico: {ingredients}\nPlano de post: {recipe_plan}")
                if "Error during agent run" in recipe_post_content:
                    raise Exception(recipe_post_content)

            except Exception as e:
                error_message = f"Um feitiço deu errado durante a conjuração da receita: {e}"

    return render_template('index.html',
                           ingredients=ingredients,
                           recipe_post_content=recipe_post_content,
                           error_message=error_message,
                           downlaoad_filename=download_filename)

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    # In a real deployment, use a production-ready server like Gunicorn or uWSGI
    app.run(debug=True)