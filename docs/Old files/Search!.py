import wikipedia
import pyttsx3 as p #as alias in python i.e duplicate name

# Set a user-agent as required by Wikimedia API policy
wikipedia.set_user_agent("MCASearchProject/1.0 (educational use)")

print("hello... welcome to trust page :)")
user = str(input("so..what you want to search!!")).strip()

try:
    # auto_suggest=False prevents wikipedia from breaking phrases like 'gen ai' into 'gen a i'
    result = wikipedia.summary(user, sentences=3, auto_suggest=False)
except wikipedia.exceptions.DisambiguationError as e:
    print(f"\nMultiple results found. Try one of these:\n{', '.join(e.options[:5])}")
    result = None
except wikipedia.exceptions.PageError:
    print(f"\nSorry, no Wikipedia page found for '{user}'.")
    result = None
except Exception as e:
    print(f"\nAn error occurred while fetching data: {e}")
    result = None

if result:
    a = str(input("do want to see the result \n press 1 for yes and 0 for no:-"))
    if a == '1':
        print("\n" + result + "\n")
        b = str(input("do you want us to read it out \n press 1 for yes and 0 for no:-"))
        if b == '1':
            p.speak(result)
        elif b == '0':
            pass
        else:
            print("Enter valid output!")
    elif a == '0':
        print("Bye..")
    else:
        print("Enter valid input!")

#DONE----Problem Solved :)
