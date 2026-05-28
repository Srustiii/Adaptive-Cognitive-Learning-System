import csv
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app import models


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = PROJECT_ROOT / "datasets"
COURSES = ["Python", "Machine Learning"]
DIFFICULTIES = {
    "easy": 0.25,
    "medium": 0.55,
    "hard": 0.85,
}


def ensure_sample_datasets() -> dict:
    """Generate realistic CSV files automatically for demo and research use."""
    DATASETS_DIR.mkdir(exist_ok=True)

    rows = _build_sample_questions()
    course_paths = {}
    for course, filename in {"Python": "python_questions.csv", "Machine Learning": "ml_questions.csv"}.items():
        course_rows = [row for row in rows if row["course"] == course]
        path = DATASETS_DIR / filename
        _write_csv(path, course_rows)
        course_paths[course] = str(path)

    return {
        "total_questions": len(rows),
        "course_files": course_paths,
    }


def seed_questions_from_csv(db: Session, csv_path: Path | str | None = None) -> int:
    """Load CSV questions into SQLite, skipping exact duplicate question text."""
    ensure_sample_datasets()
    paths = [Path(csv_path)] if csv_path else [DATASETS_DIR / "python_questions.csv", DATASETS_DIR / "ml_questions.csv"]
    created = 0

    for path in paths:
        with path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                exists = (
                    db.query(models.Question)
                    .filter(models.Question.text == row["question"])
                    .first()
                )
                if exists:
                    # If an existing question entry has an empty type, upgrade it to 'mcq'.
                    if not exists.question_type:
                        exists.question_type = row.get("question_type") or "mcq"
                        db.add(exists)
                    continue

                db.add(
                    models.Question(
                        course=row["course"],
                        topic=row["topic"],
                        difficulty=float(row["difficulty"]),
                        difficulty_label=row["difficulty_label"],
                        question_type=row.get("question_type") or "mcq",
                        text=row["question"],
                        options=json.dumps(
                            [row["option_a"], row["option_b"], row["option_c"], row["option_d"]]
                        ),
                        correct_answer=row["correct_answer"],
                        explanation=row["explanation"],
                        starter_code=row.get("starter_code") or None,
                        test_code=row.get("test_code") or None,
                    ),
                )
                created += 1

    db.commit()
    return created


def import_uploaded_csv(db: Session, file_path: Path) -> int:
    """Import a user-provided CSV with the same beginner-friendly schema."""
    return seed_questions_from_csv(db, file_path)


def _build_sample_questions() -> list[dict]:
    rows = []
    
    # 24 Handcrafted Python MCQs
    python_mcqs = [
        # Variables
        {
            "course": "Python", "topic": "variables", "difficulty_label": "easy", "difficulty": 0.25,
            "question": "Which of the following is a valid variable name in Python?",
            "option_a": "my_variable_1", "option_b": "1_variable", "option_c": "my-variable", "option_d": "global",
            "correct_answer": "A", "explanation": "Variable names in Python must start with a letter or an underscore, cannot contain hyphens, and cannot be reserved keywords like 'global'."
        },
        {
            "course": "Python", "topic": "variables", "difficulty_label": "medium", "difficulty": 0.55,
            "question": "What will be the output of executing x = [1, 2] followed by y = x and y.append(3)?",
            "option_a": "x is [1, 2, 3], y is [1, 2, 3]", "option_b": "x is [1, 2], y is [1, 2, 3]", "option_c": "x is [1, 2, 3], y is [1, 2]", "option_d": "Python raises a TypeError",
            "correct_answer": "A", "explanation": "In Python, assigning a list reference to another variable (y = x) makes both point to the same object in memory. Modifying the list through y also modifies it for x."
        },
        {
            "course": "Python", "topic": "variables", "difficulty_label": "hard", "difficulty": 0.85,
            "question": "What is the result of the following scoping behavior in Python?\n\nx = 10\ndef f():\n    global x\n    x = 20\n    def g():\n        nonlocal x\n        x = 30\n    g()\nf()\nprint(x)",
            "option_a": "SyntaxError: nonlocal variable 'x' bound at global scope", "option_b": "30", "option_c": "20", "option_d": "10",
            "correct_answer": "A", "explanation": "The 'nonlocal' keyword is used to refer to a variable in the nearest enclosing scope that is not global. Since x is declared 'global' in f(), it exists in the global scope, causing a SyntaxError in g()."
        },
        # Loops
        {
            "course": "Python", "topic": "loops", "difficulty_label": "easy", "difficulty": 0.25,
            "question": "What is the output of the loop: for i in range(3): print(i, end=' ')?",
            "option_a": "0 1 2 ", "option_b": "1 2 3 ", "option_c": "0 1 2 3 ", "option_d": "0, 1, 2",
            "correct_answer": "A", "explanation": "range(3) generates a sequence of integers starting from 0 and ending before 3 (yielding 0, 1, 2)."
        },
        {
            "course": "Python", "topic": "loops", "difficulty_label": "medium", "difficulty": 0.55,
            "question": "What does the 'else' block in a Python 'for' or 'while' loop do?",
            "option_a": "Executes only if the loop completes all iterations without encountering a 'break' statement.", "option_b": "Executes if the loop condition was false from the very beginning.", "option_c": "Executes after every single iteration of the loop.", "option_d": "Acts as a catch block if any exception occurs inside the loop.",
            "correct_answer": "A", "explanation": "In Python, the 'else' clause of a loop executes when the loop finishes naturally (meaning no 'break' statement was encountered)."
        },
        {
            "course": "Python", "topic": "loops", "difficulty_label": "hard", "difficulty": 0.85,
            "question": "What is the output of the following nested loop code?\n\nresult = []\nfor x in range(3):\n    for y in range(3):\n        if x == y:\n            break\n        result.append((x, y))\nprint(result)",
            "option_a": "[(1, 0), (2, 0), (2, 1)]", "option_b": "[(0, 0), (1, 1), (2, 2)]", "option_c": "[(0, 1), (0, 2), (1, 2)]", "option_d": "[(1, 0), (2, 0)]",
            "correct_answer": "A", "explanation": "When x == y, the inner loop breaks. For x=0, it breaks at y=0. For x=1, (1, 0) is added, then breaks at y=1. For x=2, (2, 0) and (2, 1) are added, then breaks at y=2. Thus, result is [(1, 0), (2, 0), (2, 1)]."
        },
        # Functions
        {
            "course": "Python", "topic": "functions", "difficulty_label": "easy", "difficulty": 0.25,
            "question": "What is the correct way to define a function named 'greet' that takes a parameter 'name' in Python?",
            "option_a": "def greet(name):", "option_b": "function greet(name) {", "option_c": "def greet name:", "option_d": "greet = function(name):",
            "correct_answer": "A", "explanation": "Functions in Python are defined using the 'def' keyword, followed by the function name, parameters in parentheses, and a colon."
        },
        {
            "course": "Python", "topic": "functions", "difficulty_label": "medium", "difficulty": 0.55,
            "question": "What will be the output of executing the following Python function call?\n\ndef add_item(item, box=[]):\n    box.append(item)\n    return box\nadd_item(1)\nprint(add_item(2))",
            "option_a": "[1, 2]", "option_b": "[2]", "option_c": "[1, [2]]", "option_d": "TypeError: box is not defined",
            "correct_answer": "A", "explanation": "Default arguments in Python are evaluated once at definition time. Using a mutable default argument like box=[] shares the same list across all calls that do not provide a custom list."
        },
        {
            "course": "Python", "topic": "functions", "difficulty_label": "hard", "difficulty": 0.85,
            "question": "In Python, what does the double asterisk '**' prefix signify when defining a function parameter like def f(**kwargs)?",
            "option_a": "It collects arbitrary keyword arguments passed to the function into a dictionary.", "option_b": "It allows passing a list of values as positional arguments.", "option_c": "It performs an exponentiation check on all passed arguments.", "option_d": "It forces the compiler to inline the function for optimization.",
            "correct_answer": "A", "explanation": "The '**kwargs' syntax allows a function to accept any number of keyword arguments, which are collected into a dictionary named kwargs inside the function."
        },
        # Lists
        {
            "course": "Python", "topic": "lists", "difficulty_label": "easy", "difficulty": 0.25,
            "question": "How do you access the last element of a Python list named 'items'?",
            "option_a": "items[-1]", "option_b": "items[len(items)]", "option_c": "items.last()", "option_d": "items[1]",
            "correct_answer": "A", "explanation": "Python supports negative indexing, where -1 represents the last element of the list, -2 the second last, and so on."
        },
        {
            "course": "Python", "topic": "lists", "difficulty_label": "medium", "difficulty": 0.55,
            "question": "What is the result of this list comprehension: [x**2 for x in range(5) if x % 2 == 0]?",
            "option_a": "[0, 4, 16]", "option_b": "[4, 16]", "option_c": "[0, 1, 4, 9, 16]", "option_d": "[0, 2, 4]",
            "correct_answer": "A", "explanation": "range(5) yields 0, 1, 2, 3, 4. The condition x % 2 == 0 filters even numbers: 0, 2, 4. Squaring them yields 0, 4, 16."
        },
        {
            "course": "Python", "topic": "lists", "difficulty_label": "hard", "difficulty": 0.85,
            "question": "What is the correct output when slicing list nums = [10, 20, 30, 40, 50] with nums[3:1:-1]?",
            "option_a": "[40, 30]", "option_b": "[40, 30, 20]", "option_c": "[30, 20]", "option_d": "[]",
            "correct_answer": "A", "explanation": "The slice starts at index 3 (value 40) and steps backwards by -1 up to (but excluding) index 1 (value 20). Thus, it yields indices 3 and 2, which are 40 and 30."
        },
        # Exceptions
        {
            "course": "Python", "topic": "exceptions", "difficulty_label": "easy", "difficulty": 0.25,
            "question": "Which block is always executed in a try-except structure in Python, regardless of whether an exception occurred or not?",
            "option_a": "finally", "option_b": "else", "option_c": "catch", "option_d": "always",
            "correct_answer": "A", "explanation": "The 'finally' block is executed whether an exception was raised or not, making it ideal for cleaning up resources like files or database connections."
        },
        {
            "course": "Python", "topic": "exceptions", "difficulty_label": "medium", "difficulty": 0.55,
            "question": "What is the difference between the 'except Exception as e' block and the 'else' block in Python exception handling?",
            "option_a": "The 'else' block executes only if the 'try' block completed without raising any exceptions.", "option_b": "The 'else' block executes if an exception was caught and handled successfully.", "option_c": "The 'else' block is used to declare variables that are safe from scopes.", "option_d": "There is no difference; they are interchangeable.",
            "correct_answer": "A", "explanation": "In a try-except-else block, the else block runs only if no exception was raised in the try block."
        },
        {
            "course": "Python", "topic": "exceptions", "difficulty_label": "hard", "difficulty": 0.85,
            "question": "What will happen when running this code?\n\ndef divide(a, b):\n    try:\n        return a / b\n    except ZeroDivisionError:\n        return 'Zero!'\n    finally:\n        return 'Cleaned!'\nprint(divide(10, 0))",
            "option_a": "It prints 'Cleaned!'", "option_b": "It prints 'Zero!'", "option_c": "It raises a ZeroDivisionError", "option_d": "It prints 'Cleaned!' followed by 'Zero!'",
            "correct_answer": "A", "explanation": "If a finally block executes a return statement, that return value will take precedence and discard any return value or exception from the try or except blocks."
        },
        # Strings
        {
            "course": "Python", "topic": "strings", "difficulty_label": "easy", "difficulty": 0.25,
            "question": "Which method converts a Python string to all uppercase letters?",
            "option_a": "text.upper()", "option_b": "text.toUpperCase()", "option_c": "text.capitalize()", "option_d": "text.toUpper()",
            "correct_answer": "A", "explanation": "The upper() method returns a copy of the string with all characters converted to uppercase."
        },
        {
            "course": "Python", "topic": "strings", "difficulty_label": "medium", "difficulty": 0.55,
            "question": "What is the result of 'hello'.replace('l', 'x', 1) in Python?",
            "option_a": "'hexlo'", "option_b": "'hexxo'", "option_c": "'helo'", "option_d": "TypeError: replace takes exactly 2 arguments",
            "correct_answer": "A", "explanation": "The third argument to replace() specifies the maximum number of occurrences to replace. Specifying 1 replaces only the first occurrence of 'l' with 'x'."
        },
        {
            "course": "Python", "topic": "strings", "difficulty_label": "hard", "difficulty": 0.85,
            "question": "Why are strings in Python considered 'immutable'?",
            "option_a": "Any operation that modifies a string creates and returns a completely new string object in memory.", "option_b": "They cannot be accessed by negative indexing.", "option_c": "They cannot be concatenated using the '+' operator.", "option_d": "Their memory addresses are fixed at compile time.",
            "correct_answer": "A", "explanation": "Immutability means a string object's content cannot be changed in-place. Doing so creates a new string object in memory rather than modifying the original."
        },
        # Dictionaries
        {
            "course": "Python", "topic": "dictionaries", "difficulty_label": "easy", "difficulty": 0.25,
            "question": "How do you add a new key-value pair 'a': 1 to a Python dictionary named d?",
            "option_a": "d['a'] = 1", "option_b": "d.add('a', 1)", "option_c": "d.insert('a', 1)", "option_d": "d.put('a', 1)",
            "correct_answer": "A", "explanation": "You can add a key-value pair to a dictionary by using square brackets with the key and assigning a value."
        },
        {
            "course": "Python", "topic": "dictionaries", "difficulty_label": "medium", "difficulty": 0.55,
            "question": "What will happen if you attempt to access d['missing'] on a dictionary d that does not have the key 'missing'?",
            "option_a": "It raises a KeyError", "option_b": "It returns None", "option_c": "It creates the key automatically with a value of None", "option_d": "It raises a ValueError",
            "correct_answer": "A", "explanation": "Accessing a non-existent key directly via square brackets d[key] raises a KeyError. To return a default value instead, use d.get(key)."
        },
        {
            "course": "Python", "topic": "dictionaries", "difficulty_label": "hard", "difficulty": 0.85,
            "question": "What is the output of the following dictionary comprehension code?\n\nprint({x: x**2 for x in range(3) if x > 0})",
            "option_a": "{1: 1, 2: 4}", "option_b": "{0: 0, 1: 1, 2: 4}", "option_c": "[1: 1, 2: 4]", "option_d": "{1, 4}",
            "correct_answer": "A", "explanation": "The expression generates key-value pairs where the key is x and the value is x**2 for x in 0, 1, 2 where x > 0. The only items qualifying are 1 and 2, yielding {1: 1, 2: 4}."
        },
        # Files
        {
            "course": "Python", "topic": "files", "difficulty_label": "easy", "difficulty": 0.25,
            "question": "What is the recommended statement in Python to ensure files are closed automatically after use, even if an exception occurs?",
            "option_a": "with open('file.txt') as f:", "option_b": "open('file.txt') as f:", "option_c": "try f = open('file.txt')", "option_d": "file.open('file.txt')",
            "correct_answer": "A", "explanation": "The 'with' statement utilizes a context manager which automatically manages file resources, closing the file when the block is exited."
        },
        {
            "course": "Python", "topic": "files", "difficulty_label": "medium", "difficulty": 0.55,
            "question": "Which file opening mode should you use to add text to the end of an existing file without wiping its current content?",
            "option_a": "'a'", "option_b": "'w'", "option_c": "'r'", "option_d": "'x'",
            "correct_answer": "A", "explanation": "The 'a' mode stands for append. It opens the file and positions the pointer at the end of the file, preserving any existing content."
        },
        {
            "course": "Python", "topic": "files", "difficulty_label": "hard", "difficulty": 0.85,
            "question": "What happens under the hood when a context manager is used with the 'with' statement in Python?",
            "option_a": "The runtime automatically invokes the object's __enter__() method on block entry and its __exit__() method upon block exit.", "option_b": "Python compiles the block into a thread-safe atomic transaction.", "option_c": "Memory for all variables inside the block is immediately garbage-collected.", "option_d": "The file contents are fully loaded into a system-level virtual memory buffer.",
            "correct_answer": "A", "explanation": "The context manager protocol in Python relies on defining __enter__ to setup resources and __exit__ to handle cleanup and exceptions."
        }
    ]

    # 24 Handcrafted Machine Learning MCQs
    ml_mcqs = [
        # Supervised Learning
        {
            "course": "Machine Learning", "topic": "supervised learning", "difficulty_label": "easy", "difficulty": 0.25,
            "question": "What is the main difference between Supervised and Unsupervised learning?",
            "option_a": "Supervised learning uses labeled training data, whereas unsupervised learning works on unlabeled data.", "option_b": "Supervised learning requires human presence during the training phase.", "option_c": "Unsupervised learning is used only for neural networks.", "option_d": "Supervised learning is faster than unsupervised learning.",
            "correct_answer": "A", "explanation": "Supervised learning relies on matching inputs to target outputs (labels). Unsupervised learning aims to find hidden structures or groups in data without labels."
        },
        {
            "course": "Machine Learning", "topic": "supervised learning", "difficulty_label": "medium", "difficulty": 0.55,
            "question": "Which of the following problems is a classic regression problem?",
            "option_a": "Predicting house prices based on size, location, and age.", "option_b": "Filtering incoming emails into 'Spam' and 'Not Spam'.", "option_c": "Grouping customers into distinct clusters based on shopping frequency.", "option_d": "Detecting fraudulent bank transactions in real-time.",
            "correct_answer": "A", "explanation": "Regression deals with predicting continuous numeric values (like prices). Classification deals with discrete categories (like Spam vs Not Spam)."
        },
        {
            "course": "Machine Learning", "topic": "supervised learning", "difficulty_label": "hard", "difficulty": 0.85,
            "question": "In a supervised learning environment, how does the 'inductive bias' of a model affect its behavior?",
            "option_a": "It represents the set of assumptions the model uses to predict outputs for unseen training instances.", "option_b": "It defines the artificial bias parameter added to neural network neurons.", "option_c": "It causes the model to consistently favor positive class predictions.", "option_d": "It indicates the system's human-level bias introduced during data scraping.",
            "correct_answer": "A", "explanation": "Inductive bias is the set of assumptions a learning algorithm uses to predict outputs for inputs it has not encountered during training."
        },
        # Metrics
        {
            "course": "Machine Learning", "topic": "metrics", "difficulty_label": "easy", "difficulty": 0.25,
            "question": "In classification, what is the formula for Accuracy?",
            "option_a": "(True Positives + True Negatives) / (Total Predictions)", "option_b": "(True Positives) / (True Positives + False Positives)", "option_c": "(True Positives) / (True Positives + False Negatives)", "option_d": "(True Negatives) / (True Negatives + False Positives)",
            "correct_answer": "A", "explanation": "Accuracy measures the proportion of correct predictions (both positive and negative) out of all predictions made."
        },
        {
            "course": "Machine Learning", "topic": "metrics", "difficulty_label": "medium", "difficulty": 0.55,
            "question": "In binary classification, when should you prioritize Precision over Recall?",
            "option_a": "When the cost of a False Positive is very high, such as classifying non-spam emails as spam.", "option_b": "When the cost of a False Negative is very high, such as diagnosing a life-threatening disease.", "option_c": "When the dataset is perfectly balanced between classes.", "option_d": "When the model is running under strict CPU/memory constraints.",
            "correct_answer": "A", "explanation": "Precision focuses on minimizing False Positives (i.e. of the ones predicted positive, how many are actually positive?). Recall focuses on minimizing False Negatives."
        },
        {
            "course": "Machine Learning", "topic": "metrics", "difficulty_label": "hard", "difficulty": 0.85,
            "question": "What does the Area Under the ROC Curve (ROC-AUC) measure for a binary classification model?",
            "option_a": "The probability that the model will rank a randomly chosen positive instance higher than a randomly chosen negative instance.", "option_b": "The exact ratio of correct positive predictions to incorrect negative predictions.", "option_c": "The percentage of outliers successfully filtered from the test set.", "option_d": "The speed of convergence of the gradient descent algorithm.",
            "correct_answer": "A", "explanation": "ROC-AUC evaluates how well the classifier distinguishes between classes. An AUC of 0.85 means there is an 85% chance that the model will rank a random positive item above a random negative one."
        },
        # Regression
        {
            "course": "Machine Learning", "topic": "regression", "difficulty_label": "easy", "difficulty": 0.25,
            "question": "What is the main objective of Linear Regression?",
            "option_a": "To find the line of best fit that minimizes the sum of squared differences between predicted and actual values.", "option_b": "To group variables into classes based on their distance.", "option_c": "To draw a curved boundary to separate categories.", "option_d": "To find the maximum margin between support vectors.",
            "correct_answer": "A", "explanation": "Linear regression aims to model the relationship between variables by fitting a linear equation, typically minimizing the Mean Squared Error (MSE)."
        },
        {
            "course": "Machine Learning", "topic": "regression", "difficulty_label": "medium", "difficulty": 0.55,
            "question": "Which regression metric is most sensitive to large outlier values?",
            "option_a": "Mean Squared Error (MSE)", "option_b": "Mean Absolute Error (MAE)", "option_c": "R-squared (R2)", "option_d": "Adjusted R-squared",
            "correct_answer": "A", "explanation": "MSE squares the error terms (y_true - y_pred). This means larger errors have a disproportionately large impact on the metric, making it highly sensitive to outliers compared to MAE."
        },
        {
            "course": "Machine Learning", "topic": "regression", "difficulty_label": "hard", "difficulty": 0.85,
            "question": "What is the primary difference between Lasso (L1) and Ridge (L2) regression regularizations?",
            "option_a": "Lasso can shrink coefficients completely to zero, performing feature selection, while Ridge only shrinks them close to zero.", "option_b": "Ridge regularizes by penalizing the absolute sum of coefficients, while Lasso penalizes the squared sum.", "option_c": "Lasso is used only for classification, while Ridge is used only for regression.", "option_d": "Ridge requires an active GPU environment, whereas Lasso does not.",
            "correct_answer": "A", "explanation": "Lasso adds an L1 penalty (absolute values of weights), which tends to produce sparse solutions where less important feature weights become exactly zero. Ridge adds an L2 penalty (squared weights), keeping all weights small but non-zero."
        },
        # Classification
        {
            "course": "Machine Learning", "topic": "classification", "difficulty_label": "easy", "difficulty": 0.25,
            "question": "Which of the following is a widely used classification algorithm?",
            "option_a": "Logistic Regression", "option_b": "K-Means", "option_c": "Linear Regression", "option_d": "Principal Component Analysis (PCA)",
            "correct_answer": "A", "explanation": "Despite having 'Regression' in its name, Logistic Regression is a fundamental binary classification algorithm that outputs class probabilities."
        },
        {
            "course": "Machine Learning", "topic": "classification", "difficulty_label": "medium", "difficulty": 0.55,
            "question": "How does a Decision Tree classifier decide where to split a node?",
            "option_a": "By maximizing information gain or minimizing Gini impurity.", "option_b": "By calculating the Euclidean distance between feature coordinates.", "option_c": "By performing gradient descent on weight vectors.", "option_d": "By selecting a random split threshold for each feature.",
            "correct_answer": "A", "explanation": "Decision trees partition data by choosing splits that lead to maximum homogeneity (purity) in the child nodes, measured via Gini Impurity or Information Gain (Entropy)."
        },
        {
            "course": "Machine Learning", "topic": "classification", "difficulty_label": "hard", "difficulty": 0.85,
            "question": "What is the role of 'Support Vectors' in a Support Vector Machine (SVM) classifier?",
            "option_a": "They are the critical data points closest to the decision boundary that define the margin's position.", "option_b": "They are virtual vectors created to represent average class coordinates.", "option_c": "They are regularization coefficients used to balance bias and variance.", "option_d": "They are scaling factors used to encode categorical parameters.",
            "correct_answer": "A", "explanation": "Support vectors are the training examples that lie closest to the decision surface. Removing them would change the position of the separating hyperplane."
        },
        # Features
        {
            "course": "Machine Learning", "topic": "features", "difficulty_label": "easy", "difficulty": 0.25,
            "question": "What is the goal of Feature Scaling in machine learning?",
            "option_a": "To bring all features to a similar numerical scale, preventing features with larger values from dominating.", "option_b": "To reduce the physical storage size of dataset files.", "option_c": "To increase the number of columns in the dataset.", "option_d": "To automatically delete rows with missing coordinates.",
            "correct_answer": "A", "explanation": "Algorithms relying on distances (like KNN or SVM) or gradients (like neural networks) perform poorly if features have vastly different scales. Feature scaling normalizes their ranges."
        },
        {
            "course": "Machine Learning", "topic": "features", "difficulty_label": "medium", "difficulty": 0.55,
            "question": "What is the difference between Normalization (Min-Max Scaling) and Standardization (Z-score Normalization)?",
            "option_a": "Normalization bounds values strictly between 0 and 1, whereas Standardization centers values around mean 0 with standard deviation 1.", "option_b": "Standardization bounds values between 0 and 1, whereas Normalization centers them.", "option_c": "Normalization is used for numeric data, whereas Standardization is used only for text columns.", "option_d": "Normalization requires calculating the median, whereas Standardization requires the mode.",
            "correct_answer": "A", "explanation": "Min-Max scaling normalizes data to a fixed range (typically 0 to 1). Z-score standardization transforms data to have a mean of 0 and standard deviation of 1, which handles outliers better."
        },
        {
            "course": "Machine Learning", "topic": "features", "difficulty_label": "hard", "difficulty": 0.85,
            "question": "When dealing with high-cardinality categorical features, why is One-Hot Encoding sometimes problematic?",
            "option_a": "It creates a very high number of sparse binary columns, leading to the curse of dimensionality.", "option_b": "It converts categorical strings into invalid floating-point numbers.", "option_c": "It destroys the linear relationship between the independent and dependent variables.", "option_d": "It causes the models to ignore regularized coefficients.",
            "correct_answer": "A", "explanation": "One-hot encoding creates a column for every single unique category. For a column with 1,000 categories, it adds 1,000 columns, vastly increasing dimensionality and sparse data overhead."
        },
        # Overfitting
        {
            "course": "Machine Learning", "topic": "overfitting", "difficulty_label": "easy", "difficulty": 0.25,
            "question": "What does it mean when a machine learning model is 'overfitting'?",
            "option_a": "The model performs exceptionally well on the training data but fails to generalize to unseen test data.", "option_b": "The model's training accuracy is too low.", "option_c": "The model requires too much memory to load.", "option_d": "The dataset has more columns than rows.",
            "correct_answer": "A", "explanation": "Overfitting occurs when a model learns the noise and details of the training set too well, leading to poor generalization on new, unseen data."
        },
        {
            "course": "Machine Learning", "topic": "overfitting", "difficulty_label": "medium", "difficulty": 0.55,
            "question": "How does increasing the regularization parameter (lambda/alpha) affect a model's bias and variance?",
            "option_a": "It increases bias and decreases variance, simplifying the model.", "option_b": "It decreases bias and increases variance, making the model more complex.", "option_c": "It decreases both bias and variance.", "option_d": "It has no effect on bias or variance.",
            "correct_answer": "A", "explanation": "Regularization penalizes model complexity. Increasing the penalty forces weights to be smaller, which reduces variance (less overfitting) but increases bias (simpler model)."
        },
        {
            "course": "Machine Learning", "topic": "overfitting", "difficulty_label": "hard", "difficulty": 0.85,
            "question": "How does Cross-Validation help in diagnosing overfitting?",
            "option_a": "By providing an unbiased estimate of model performance on multiple validation folds, showing if training score is significantly higher than validation score.", "option_b": "By automatically pruning decision tree branches.", "option_c": "By removing collinear features before the training loop starts.", "option_d": "By training the model on the testing set directly.",
            "correct_answer": "A", "explanation": "Cross-validation splits the training data into multiple folds. If the model scores very high on the training fold but drops significantly on the validation folds, it is a clear indicator of overfitting."
        },
        # Clustering
        {
            "course": "Machine Learning", "topic": "clustering", "difficulty_label": "easy", "difficulty": 0.25,
            "question": "Which of the following is a classic unsupervised clustering algorithm?",
            "option_a": "K-Means", "option_b": "Logistic Regression", "option_c": "Linear Regression", "option_d": "Decision Trees",
            "correct_answer": "A", "explanation": "K-Means is a popular unsupervised algorithm that partitions unlabeled data into K clusters based on similarity."
        },
        {
            "course": "Machine Learning", "topic": "clustering", "difficulty_label": "medium", "difficulty": 0.55,
            "question": "In K-Means clustering, what does the 'Elbow Method' help you determine?",
            "option_a": "The optimal number of clusters (K) by plotting the sum of squared distances against K.", "option_b": "The execution time of the clustering loop.", "option_c": "The maximum distance between support vectors.", "option_d": "The optimal feature scaling factor.",
            "correct_answer": "A", "explanation": "The elbow method plots the within-cluster sum of squares (inertia) as a function of K. The 'elbow' point indicates a balanced trade-off where increasing K yields diminishing returns."
        },
        {
            "course": "Machine Learning", "topic": "clustering", "difficulty_label": "hard", "difficulty": 0.85,
            "question": "What is measured by the Silhouette Coefficient in clustering analysis?",
            "option_a": "How close each point in one cluster is to points in the neighboring clusters, balancing cohesion and separation.", "option_b": "The exact ratio of outliers successfully removed.", "option_c": "The rate of convergence of centroid recalculations.", "option_d": "The overlap between supervised class boundaries.",
            "correct_answer": "A", "explanation": "The Silhouette Coefficient measures clustering quality by evaluating both cohesion (how close a point is to its own cluster members) and separation (how far it is from the nearest neighboring cluster). Scores range from -1 to 1."
        },
        # Model Validation
        {
            "course": "Machine Learning", "topic": "model validation", "difficulty_label": "easy", "difficulty": 0.25,
            "question": "Why is it critical to split your data into a training set and a testing set?",
            "option_a": "To evaluate how well the model generalizes to new, unseen data.", "option_b": "To make sure the training runs twice as fast.", "option_c": "To filter out duplicate rows.", "option_d": "Because modern libraries will not execute training without a split.",
            "correct_answer": "A", "explanation": "Evaluating a model on the same data it trained on is cheating. A separate test set provides an honest, unbiased estimation of generalization performance."
        },
        {
            "course": "Machine Learning", "topic": "model validation", "difficulty_label": "medium", "difficulty": 0.55,
            "question": "What is K-Fold Cross-Validation?",
            "option_a": "A validation technique where data is split into K equal folds; the model is trained K times, each time using a different fold for validation.", "option_b": "A method that scales learning rates by a factor of K.", "option_c": "A regression algorithm that fits K lines to the data.", "option_d": "A data scrubbing technique that deletes every K-th row.",
            "correct_answer": "A", "explanation": "K-Fold cross-validation ensures every data point is used for training and validation exactly once, leading to a much more robust performance estimation."
        },
        {
            "course": "Machine Learning", "topic": "model validation", "difficulty_label": "hard", "difficulty": 0.85,
            "question": "What is the difference between a Validation Curve and a Learning Curve?",
            "option_a": "A Validation Curve plots performance against a hyperparameter, while a Learning Curve plots performance against training sample size.", "option_b": "A Learning Curve is used only for deep learning, whereas a Validation Curve is used for classic ML.", "option_c": "A Validation Curve displays training time, whereas a Learning Curve displays scoring latency.", "option_d": "There is no difference; they are different terms for the same plot.",
            "correct_answer": "A", "explanation": "Validation Curves show how a model's score varies with a hyperparameter (e.g. max_depth). Learning Curves show how the score varies with the number of training samples, helping diagnose bias vs variance."
        }
    ]

    rows.extend(python_mcqs)
    rows.extend(ml_mcqs)
    rows.extend(_coding_questions())
    return rows


def _coding_questions() -> list[dict]:
    return [
        _coding_row("Python", "loops", "easy", 0.25, "Write a function sum_numbers(values) that returns the sum of a list.", "def sum_numbers(values):\n    pass", "assert sum_numbers([1, 2, 3]) == 6\nassert sum_numbers([]) == 0"),
        _coding_row("Python", "strings", "medium", 0.55, "Write count_vowels(text) that returns the number of vowels.", "def count_vowels(text):\n    pass", "assert count_vowels('Adaptive') == 4\nassert count_vowels('xyz') == 0"),
        _coding_row("Python", "lists", "hard", 0.85, "Write unique_sorted(values) that returns sorted unique values.", "def unique_sorted(values):\n    pass", "assert unique_sorted([3, 1, 3, 2]) == [1, 2, 3]"),
        _coding_row("Machine Learning", "metrics", "easy", 0.25, "Write accuracy_score(y_true, y_pred) for equal-length label lists.", "def accuracy_score(y_true, y_pred):\n    pass", "assert accuracy_score([1,0,1], [1,1,1]) == 2/3"),
        _coding_row("Machine Learning", "features", "medium", 0.55, "Write min_max_scale(values) returning values scaled between 0 and 1.", "def min_max_scale(values):\n    pass", "assert min_max_scale([2, 4, 6]) == [0.0, 0.5, 1.0]"),
        _coding_row("Machine Learning", "activation", "hard", 0.85, "Write relu(values) that replaces negative numbers with zero.", "def relu(values):\n    pass", "assert relu([-2, 0, 3]) == [0, 0, 3]"),
    ]


def _coding_row(course, topic, label, difficulty, question, starter, tests):
    return {
        "course": course,
        "topic": topic,
        "difficulty_label": label,
        "difficulty": difficulty,
        "question_type": "coding",
        "question": question,
        "option_a": "",
        "option_b": "",
        "option_c": "",
        "option_d": "",
        "correct_answer": "tests",
        "explanation": "Solve the function so the hidden-style checks pass.",
        "starter_code": starter,
        "test_code": tests,
    }


def _write_csv(path: Path, rows: list[dict]):
    if not rows:
        return

    all_keys = []
    for row in rows:
        for key in row.keys():
            if key not in all_keys:
                all_keys.append(key)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=all_keys)
        writer.writeheader()
        writer.writerows(rows)


def _slug(value: str) -> str:
    return value.lower().replace(" ", "_")
