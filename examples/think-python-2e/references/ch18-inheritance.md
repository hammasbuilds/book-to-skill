# Chapter 18: Inheritance

Source pages 193-204 of the PDF.

## When to use

Open this file for questions about: cards, deck, rank names, hands, suit, class, inheritance, poker.

## Sections

The language feature most often associated with object-oriented programming is inheritance. Inheritance is the ability to define a new class that is a modified version of an existing class.

### 18.1 Card objects

There are fifty-two cards in a deck, each of which belongs to one of four suits and one of thirteen ranks. The suits are Spades, Hearts, Diamonds, and Clubs (in descending order in bridge).

### 18.2 Class attributes

In order to print Card objects in a way that people can easily read, we need a mapping from the integer codes to the corresponding ranks and suits. A natural way to do that is with lists of strings.

### 18.3 Comparing cards

For built-in types, there are relational operators (<, >, ==, etc.) that compare values and determine when one is greater than, less than, or equal to another. For programmer-defined types, we can override the behavior of the built-in operators by providing a method named __lt__, which stands for “less than”.

### 18.4 Decks

Now that we have Cards, the next step is to define Decks. Since a deck is made up of cards, it is natural for each Deck to contain a list of cards as an attribute.

### 18.5 Printing the deck

Here is a __str__ method for Deck:

### 18.6 Add, remove, shuffle and sort

To deal cards, we would like a method that removes a card from the deck and returns it. The list method pop provides a convenient way to do that:

### 18.7 Inheritance

Inheritance is the ability to define a new class that is a modified version of an existing class. As an example, let’s say we want a class to represent a “hand”, that is, the cards held by one player.

### 18.8 Class diagrams

So far we have seen stack diagrams, which show the state of a program, and object diagrams, which show the attributes of an object and their values. These diagrams represent a snapshot in the execution of a program, so they change as the program runs.

### 18.9 Debugging

Inheritance can make debugging difficult because when you invoke a method on an object, it might be hard to figure out which method will be invoked.

### 18.10 Data encapsulation

The previous chapters demonstrate a development plan we might call “object-oriented design”. We identified objects we needed—like Point, Rectangle and Time—and defined classes to represent them.

### 18.12 Exercises

Exercise 18.1. For the following program, draw a UML class diagram that shows these classes and the relationships among them.

## Key definitions

- In this context, “encode” means that we are going to define a mapping between numbers and suits, or between numbers and ranks.
- Variables like suit_names and rank_names, which are defined inside a class but outside of any method, are called class attributes because they are associated with the class object Card.
- This term distinguishes them from variables like suit and rank, which are called instance attributes because they are associated with a particular instance.
- For programmer-defined types, we can override the behavior of the built-in operators by providing a method named __lt__, which stands for “less than”.
- When a new class inherits from an existing one, the existing one is called the parent and the new class is called the child.
- This kind of relationship is called HAS-A, as in, “a Rectangle has a Point.”
- This relationship is called IS-A, as in, “a Hand is a kind of a Deck.”
- This kind of relationship is called a dependency.
- find_defining_class uses the mro method to get the list of class objects (types) that will be searched for methods. “MRO” stands for “method resolution order”, which is the sequence of classes Python searches to “resolve” a method name.
- If you violate this rule, which is called the “Liskov substitution principle”, your code will collapse like (sorry) a house of cards.

## Worked examples

From *Card objects*: The class definition for Card looks like this:

```
class Card:
    """Represents a standard playing card."""

    def __init__(self, suit=0, rank=2):
        self.suit = suit
        self.rank = rank
```

From *Class attributes*: We assign these lists to class attributes:

```
# inside class Card:

    suit_names = ['Clubs', 'Diamonds', 'Hearts', 'Spades']
    rank_names = [None, 'Ace', '2', '3', '4', '5', '6', '7',
              '8', '9', '10', 'Jack', 'Queen', 'King']

    def __str__(self):
        return '%s of %s' % (Card.rank_names[self.rank],
                             Card.suit_names[self.suit])
```

From *Comparing cards*: With that decided, we can write __lt__:

```
# inside class Card:

    def __lt__(self, other):
        # check the suits
        if self.suit < other.suit: return True
        if self.suit > other.suit: return False

        # suits are the same... check ranks
        return self.rank < other.rank
```

From *Decks*: The init method creates the attribute cards and generates the standard set of fifty-two cards:

```
class Deck:

    def __init__(self):
        self.cards = []
        for suit in range(4):
            for rank in range(1, 14):
                card = Card(suit, rank)
                self.cards.append(card)
```
