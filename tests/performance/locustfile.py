from locust import HttpUser, task
import os

# Function to replace environment variables with their values in a URL
def replace_variables(url, variables):
    path = url
    for key, value in variables.items():
        if key == "HOST":
            path = path.replace(f"$({key})", '')
        else:
            path = path.replace(f"$({key})", value)
    return path

# Read the file
file_path = 'urls.txt'  # Replace with the path to your txt file
variables = {}
paths = []

with open(file_path, 'r') as file:
    lines = file.readlines()

    # Set environment variables from the first 5 lines
    for i in range(4):
        key, value = lines[i].strip().split('=', 1)
        print(f"Setting environment variable {key} to {value}")
        variables[key] = value
        if key == "HOST":
            key = f"LOCUST_{key}"
            os.environ[key] = value

    # Replace environment variables in the paths and append to the list
    for url in lines[5:]:
        paths.append(replace_variables(url.strip(), variables))

class HelloWorldUser(HttpUser):
    @task
    def hello_world(self):
        print("Running task")
        for path in paths:
            self.client.get(path)
