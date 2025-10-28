from faker import Faker
import random
import re

def generate_creative_username(first_name, last_name):
    """
    Generate realistic usernames with human-like patterns.
    Most people use simple names, some add numbers, very few use substitutions.
    """
    # Character substitution mappings (used sparingly)
    char_substitutions = {
        'a': ['a', '4'],
        'e': ['e', '3'],
        'i': ['i', '1'],
        'o': ['o', '0'],
        'l': ['l', '1'],
        's': ['s', '5'],
        't': ['t', '7'],
        'g': ['g', '9'],
        'b': ['b', '8'],
    }

    def apply_limited_substitutions(text, max_substitutions=2):
        """
        Apply character substitutions but limit how many.
        Most people don't go crazy with leet speak.
        """
        result = list(text.lower())
        substitution_count = 0
        indices = list(range(len(result)))
        random.shuffle(indices)

        for i in indices:
            if substitution_count >= max_substitutions:
                break
            char = result[i]
            if char in char_substitutions and random.random() < 0.4:
                # Don't always substitute, and keep original as an option
                options = char_substitutions[char]
                result[i] = random.choice(options)
                if result[i] != char:  # Only count if actually substituted
                    substitution_count += 1

        return ''.join(result)

    # Decide on username style with realistic probabilities
    style_choice = random.random()

    # 40% - Simple: just firstname + lastname (most common)
    if style_choice < 0.40:
        strategies = [
            first_name.lower() + last_name.lower(),
            last_name.lower() + first_name.lower(),
            first_name.lower() + '.' + last_name.lower(),
            first_name.lower() + '_' + last_name.lower(),
        ]
        base_username = random.choice(strategies)
        use_substitutions = False
        use_numbers = random.random() < 0.3  # 30% add numbers

    # 25% - Initial + Name
    elif style_choice < 0.65:
        strategies = [
            first_name[0].lower() + last_name.lower(),
            first_name.lower() + last_name[0].lower(),
            last_name[0].lower() + first_name.lower(),
        ]
        base_username = random.choice(strategies)
        use_substitutions = False
        use_numbers = random.random() < 0.4  # 40% add numbers

    # 20% - Partial names (shortened)
    elif style_choice < 0.85:
        first_len = random.randint(3, min(6, len(first_name)))
        last_len = random.randint(3, min(6, len(last_name)))
        first_part = first_name.lower()[:first_len]
        last_part = last_name.lower()[:last_len]

        if random.random() < 0.5:
            base_username = first_part + last_part
        else:
            base_username = last_part + first_part

        use_substitutions = random.random() < 0.2  # 20% use substitutions
        use_numbers = random.random() < 0.6  # 60% add numbers

    # 15% - Creative/quirky (this is where substitutions are more common)
    else:
        first_len = random.randint(3, len(first_name))
        last_len = random.randint(3, len(last_name))
        first_part = first_name.lower()[:first_len]
        last_part = last_name.lower()[:last_len]

        base_username = random.choice([
            first_part + last_part,
            last_part + first_part,
            first_name.lower() + last_name.lower(),
        ])

        use_substitutions = random.random() < 0.5  # 50% use substitutions
        use_numbers = random.random() < 0.7  # 70% add numbers

    # Apply substitutions if decided (and limit them)
    if use_substitutions:
        max_subs = random.randint(1, 3)  # At most 1-3 character substitutions
        base_username = apply_limited_substitutions(base_username, max_subs)

    # Remove any dots/underscores for now (we'll handle length first)
    base_username = base_username.replace('.', '').replace('_', '')

    # Add numbers if decided
    if use_numbers:
        number_strategies = [
            lambda: str(random.randint(1, 99)),  # 1-99 (most common)
            lambda: str(random.randint(100, 999)),  # 100-999
            lambda: str(random.randint(1990, 2005)),  # Birth year-like
            lambda: str(random.randint(1, 9)),  # Single digit
            lambda: str(random.randint(10, 99)) + str(random.randint(10, 99)),  # Double digits
        ]

        # Weight towards simpler numbers
        weights = [0.4, 0.2, 0.2, 0.1, 0.1]
        number_part = random.choices(number_strategies, weights=weights)[0]()

        # Usually at the end (90% of the time)
        if random.random() < 0.9:
            base_username = base_username + number_part
        else:
            base_username = number_part + base_username

    # Ensure username starts with a letter
    while base_username and not base_username[0].isalpha():
        base_username = base_username[1:]

    # Handle length requirements (13-25 for Outlook)
    # But be more natural about it
    if len(base_username) < 13:
        # Pad naturally
        padding_options = [
            lambda: base_username + str(random.randint(10, 99)),
            lambda: base_username + str(random.randint(100, 999)),
            lambda: base_username + (first_name + last_name).lower()[:13 - len(base_username)],
        ]
        base_username = random.choice(padding_options)()

    # If still too short, keep adding
    while len(base_username) < 13:
        if random.random() < 0.6:
            base_username += str(random.randint(0, 9))
        else:
            base_username += random.choice((first_name + last_name).lower())

    # If too long, trim it (prefer keeping it shorter rather than max length)
    if len(base_username) > 25:
        base_username = base_username[:25]
    elif len(base_username) > 20 and random.random() < 0.5:
        # 50% chance to trim to a nicer length if it's getting long
        base_username = base_username[:random.randint(15, 20)]

    # Final cleanup - ensure only alphanumeric
    base_username = ''.join(c for c in base_username if c.isalnum())

    # Ensure it starts with a letter and meets minimum length
    while base_username and not base_username[0].isalpha():
        base_username = base_username[1:]

    # Final length check
    if len(base_username) < 13:
        base_username += str(random.randint(1000, 9999))

    return base_username[:25]  # Hard cap at 25


def generate_fake_data():
    fake = Faker()

    first_name = fake.first_name()
    last_name = fake.last_name()

    # Generate creative username based on first and last name
    login = generate_creative_username(first_name, last_name)

    # Ensure login is valid and has proper length
    while len(login) < 8 or not login[0].isalpha():
        login = generate_creative_username(first_name, last_name)

    password = fake.password(length=random.randint(13, 25), special_chars=False)

    while len(re.findall(r"\d", password)) < 2:
        password = fake.password(length=random.randint(13, 25), special_chars=False)

    # Ensure 19+ age (minimum_age=19 guarantees they are at least 19 years old)
    birth_date = fake.date_of_birth(minimum_age=19, maximum_age=35)

    return login, password, first_name, last_name, birth_date