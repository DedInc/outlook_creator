from faker import Faker
import random
import re

def generate_fake_data():
    fake = Faker()

    long_login = ''.join(e for e in (fake.user_name() * 10) if e.isalnum())

    while not long_login[0].isalpha():
        long_login = ''.join(e for e in (fake.user_name() * 10) if e.isalnum())

    login_length = random.randint(13, 25)
    login = long_login[:login_length]

    password = fake.password(length=random.randint(13, 25), special_chars=False)

    while len(re.findall(r"\d", password)) < 2:
        password = fake.password(length=random.randint(13, 25), special_chars=False)

    first_name = fake.first_name()
    last_name = fake.last_name()

    # Ensure 19+ age (minimum_age=19 guarantees they are at least 19 years old)
    birth_date = fake.date_of_birth(minimum_age=19, maximum_age=35)

    return login, password, first_name, last_name, birth_date