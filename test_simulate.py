import subprocess

def run_sim():
    with open("bad_app.py", "w") as f:
        f.write("def myMultiple(x, y):\n    return x * y\n    syntax error here\n")
    
    with open("test_bad_app.py", "w") as f:
        f.write("import unittest\nfrom bad_app import myMultiple\nclass TestApp(unittest.TestCase):\n    def test_my(self):\n        pass\n")

    res = subprocess.run(["python", "-m", "unittest", "discover"], capture_output=True, text=True)
    print("Return code:", res.returncode)
    print("STDOUT:", res.stdout)
    print("STDERR:", res.stderr)

run_sim()
