from flask import Flask, request, jsonify, render_template
from writer_agent import writer_agent
from critic_agent import critic_agent

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    topic = data.get('topic', 'General')
    notes = data.get('notes', '')
    max_attempts = int(data.get('max_attempts', 3))
    
    attempt = 1
    attempts_history = []
    
    current_input = f"Original Notes:\n{notes}"
    document = writer_agent(topic, current_input)
    
    while attempt <= max_attempts:
        review = critic_agent(topic, document)
        
        history_item = {
            "attempt": attempt,
            "document": document,
            "review": review
        }
        attempts_history.append(history_item)
        
        if "STATUS: approved" in review.lower() or "status: approved" in review.lower() or "status: approved" in review:
            break
            
        if attempt < max_attempts:
            improvement_prompt = f"""
            Topic: {topic}
            
            Original Notes:
            {notes}
            
            Critic Feedback:
            {review}
            
            Improve the document using this feedback. Ensure all previous constraints are met.
            """
            document = writer_agent(topic, improvement_prompt)
            
        attempt += 1
        
    return jsonify({
        "success": True,
        "attempts": attempts_history,
        "final_document": document
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
