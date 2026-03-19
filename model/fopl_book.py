from datetime import datetime
from sqlalchemy.exc import IntegrityError
from __init__ import app, db


class FoplBook(db.Model):
    __tablename__ = 'fopl_books'

    id          = db.Column(db.Integer,     primary_key=True)
    _title      = db.Column(db.String(255), nullable=False)
    _author     = db.Column(db.String(255), nullable=False)
    _series     = db.Column(db.String(255), nullable=True)
    _series_num = db.Column(db.Integer,     nullable=True)
    _genre      = db.Column(db.String(100), nullable=False)
    _age_group  = db.Column(db.String(50),  nullable=False)   # Kids | Middle Grade | YA | Adult
    _price      = db.Column(db.Float,       nullable=False)
    _condition  = db.Column(db.String(20),  nullable=False)   # Good | Very Good | Like New
    _quantity   = db.Column(db.Integer,     default=1, nullable=False)
    _description= db.Column(db.Text,        nullable=True)
    _isbn       = db.Column(db.String(20),  nullable=True)
    added_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    @property
    def title(self):       return self._title
    @property
    def author(self):      return self._author
    @property
    def available(self):   return self._quantity > 0

    def read(self):
        return {
            'id':          self.id,
            'title':       self._title,
            'author':      self._author,
            'series':      self._series,
            'series_num':  self._series_num,
            'genre':       self._genre,
            'age_group':   self._age_group,
            'price':       self._price,
            'condition':   self._condition,
            'quantity':    self._quantity,
            'description': self._description,
            'isbn':        self._isbn,
        }

    def create(self):
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except IntegrityError:
            db.session.rollback()
            return None

    def update(self, data):
        for k, v in data.items():
            setattr(self, f'_{k}' if not k.startswith('_') else k, v)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


def initFoplBooks():
    with app.app_context():
        db.create_all()
        if FoplBook.query.count() > 0:
            return

        books = [
            # ── Kids (Ages 4–10) ──────────────────────────────────────────────
            ('Dog Man', 'Dav Pilkey', 'Dog Man', 1, 'Comedy/Adventure', 'Kids', 1.50, 'Like New', 2, '9780545581608',
             'A crime-fighting dog-cop duo saves the day in this hilarious graphic novel series loved by early readers.'),
            ('Dog Man Unleashed', 'Dav Pilkey', 'Dog Man', 2, 'Comedy/Adventure', 'Kids', 1.50, 'Very Good', 1, '9780545581615',
             'Dog Man is back and ready to unleash justice in this action-packed sequel.'),
            ('Dog Man: A Tale of Two Kitties', 'Dav Pilkey', 'Dog Man', 3, 'Comedy/Adventure', 'Kids', 1.75, 'Like New', 2, '9780545935210',
             'Petey the Cat clones himself and chaos erupts — Dog Man must sort it all out.'),
            ('Dog Man: Lord of the Fleas', 'Dav Pilkey', 'Dog Man', 5, 'Comedy/Adventure', 'Kids', 1.75, 'Very Good', 1, '9780545935241',
             'A new villain rises and Dog Man must assemble a team of unlikely heroes to stop him.'),
            ('Dog Man: Brawl of the Wild', 'Dav Pilkey', 'Dog Man', 6, 'Comedy/Adventure', 'Kids', 1.50, 'Good', 2, '9781338236576',
             "Dog Man has gone feral — and only his friends can bring him back before it's too late."),
            ('Dog Man: For Whom the Ball Rolls', 'Dav Pilkey', 'Dog Man', 7, 'Comedy/Adventure', 'Kids', 1.50, 'Like New', 1, '9781338236590',
             'Dog Man faces his biggest challenges yet while 80-HD discovers his true purpose.'),
            ('Captain Underpants and the Attack of the Talking Toilets', 'Dav Pilkey', 'Captain Underpants', 2, 'Comedy/Adventure', 'Kids', 1.25, 'Good', 2, '9780590846288',
             'George and Harold must stop an army of evil talking toilets before they devour the entire school.'),
            ('Captain Underpants and the Perilous Plot of Professor Poopypants', 'Dav Pilkey', 'Captain Underpants', 4, 'Comedy/Adventure', 'Kids', 1.25, 'Very Good', 1, '9780439049962',
             'Professor Poopypants wants to force the world to change their names — Captain Underpants must stop him.'),

            # ── Middle Grade (Ages 8–12) ──────────────────────────────────────
            ('Diary of a Wimpy Kid', 'Jeff Kinney', 'Diary of a Wimpy Kid', 1, 'Humor/Fiction', 'Middle Grade', 2.00, 'Like New', 2, '9780810993136',
             'Greg Heffley documents his first year of middle school in a hilarious comic-diary format.'),
            ('Diary of a Wimpy Kid: Rodrick Rules', 'Jeff Kinney', 'Diary of a Wimpy Kid', 2, 'Humor/Fiction', 'Middle Grade', 2.00, 'Very Good', 1, '9780810994737',
             'Greg battles his older brother Rodrick and tries to keep an embarrassing summer secret buried.'),
            ('Diary of a Wimpy Kid: The Last Straw', 'Jeff Kinney', 'Diary of a Wimpy Kid', 3, 'Humor/Fiction', 'Middle Grade', 1.75, 'Good', 2, '9780810970687',
             "Greg's dad decides the family needs some serious changes — and military school is on the list."),
            ('Diary of a Wimpy Kid: Dog Days', 'Jeff Kinney', 'Diary of a Wimpy Kid', 4, 'Humor/Fiction', 'Middle Grade', 1.75, 'Very Good', 1, '9780810983915',
             "Greg's summer plans spiral out of control in the funniest school-vacation installment yet."),
            ('Diary of a Wimpy Kid: The Ugly Truth', 'Jeff Kinney', 'Diary of a Wimpy Kid', 5, 'Humor/Fiction', 'Middle Grade', 2.00, 'Like New', 2, '9780810984912',
             'Greg and Rowley have a falling-out and Greg must face some hard truths about growing up.'),
            ('Big Nate: In a Class by Himself', 'Lincoln Peirce', 'Big Nate', 1, 'Humor/Fiction', 'Middle Grade', 1.50, 'Good', 2, '9780062086914',
             "Nate Wright predicts he'll have the most amazing day of his life — and things go hilariously wrong."),
            ('Big Nate Strikes Again', 'Lincoln Peirce', 'Big Nate', 2, 'Humor/Fiction', 'Middle Grade', 1.50, 'Very Good', 1, '9780062086921',
             'Nate must survive a group project with his arch-nemesis Gina while chasing a school record.'),
            ('Magic Tree House: Dinosaurs Before Dark', 'Mary Pope Osborne', 'Magic Tree House', 1, 'Adventure', 'Middle Grade', 1.00, 'Good', 3, '9780679824114',
             'Jack and Annie discover a magic tree house and travel back to the age of the dinosaurs.'),
            ('Magic Tree House: The Knight at Dawn', 'Mary Pope Osborne', 'Magic Tree House', 2, 'Adventure', 'Middle Grade', 1.00, 'Very Good', 2, '9780679847373',
             'Jack and Annie travel to a medieval castle full of danger and must escape before dawn.'),
            ('Magic Tree House: Mummies in the Morning', 'Mary Pope Osborne', 'Magic Tree House', 3, 'Adventure', 'Middle Grade', 1.00, 'Like New', 2, '9780679824121',
             'The magic tree house whisks Jack and Annie to ancient Egypt where a ghost queen needs their help.'),
            ('Hatchet', 'Gary Paulsen', None, None, 'Adventure/Survival', 'Middle Grade', 2.00, 'Very Good', 1, '9781416936473',
             'Thirteen-year-old Brian must survive alone in the Canadian wilderness after a plane crash.'),
            ('The Lightning Thief', 'Rick Riordan', 'Percy Jackson', 1, 'Fantasy/Adventure', 'Middle Grade', 2.00, 'Like New', 2, '9780786838653',
             "Percy Jackson discovers he's the son of a Greek god and must retrieve Zeus's stolen lightning bolt."),
            ('The Sea of Monsters', 'Rick Riordan', 'Percy Jackson', 2, 'Fantasy/Adventure', 'Middle Grade', 2.00, 'Very Good', 1, '9780786856862',
             'Percy and Annabeth sail into the Sea of Monsters to rescue their satyr friend Grover.'),
            ('The Titan\'s Curse', 'Rick Riordan', 'Percy Jackson', 3, 'Fantasy/Adventure', 'Middle Grade', 2.00, 'Like New', 2, '9780786838677',
             'Percy must rescue the goddess Artemis and his friend Annabeth before the winter solstice.'),

            # ── Alan Gratz ────────────────────────────────────────────────────
            ('Refugee', 'Alan Gratz', None, None, 'Historical Fiction', 'Middle Grade', 2.50, 'Like New', 3, '9780545880831',
             'Three children from 1939 Germany, 1994 Cuba, and 2015 Syria flee their homelands in parallel stories of survival.'),
            ('Prisoner B-3087', 'Alan Gratz', None, None, 'Historical Fiction', 'Middle Grade', 2.00, 'Very Good', 2, '9780545459013',
             'Based on a true story: a young Jewish boy survives ten different Nazi concentration camps during WWII.'),
            ('Grenade', 'Alan Gratz', None, None, 'Historical Fiction', 'Middle Grade', 2.25, 'Like New', 2, '9781338245721',
             'An American soldier and an Okinawan boy converge in the brutal final days of the Battle of Okinawa.'),
            ('Ground Zero', 'Alan Gratz', None, None, 'Historical Fiction', 'Middle Grade', 2.50, 'Very Good', 2, '9781338245769',
             'A boy in Afghanistan on 9/11 and an Afghan refugee girl in America in 2019 discover how their lives connect.'),
            ('Allies', 'Alan Gratz', None, None, 'Historical Fiction', 'Middle Grade', 2.25, 'Like New', 1, '9781338245813',
             'Multiple perspectives converge on D-Day, June 6, 1944 — a gripping story of courage and sacrifice.'),
            ('Code of Honor', 'Alan Gratz', None, None, 'Thriller', 'YA', 2.00, 'Good', 1, '9780062292612',
             "When his decorated Army brother is branded a terrorist, Kamran Smith races to uncover the truth."),

            # ── Young Adult (Ages 13–17) ──────────────────────────────────────
            ('Harry Potter and the Sorcerer\'s Stone', 'J.K. Rowling', 'Harry Potter', 1, 'Fantasy', 'YA', 2.50, 'Like New', 2, '9780439708180',
             'An orphaned boy discovers he is a wizard and begins his journey at Hogwarts School of Witchcraft and Wizardry.'),
            ('Harry Potter and the Chamber of Secrets', 'J.K. Rowling', 'Harry Potter', 2, 'Fantasy', 'YA', 2.50, 'Very Good', 1, '9780439064873',
             'Harry returns to Hogwarts to find a mysterious monster is petrifying students and writing threatening messages.'),
            ('Harry Potter and the Prisoner of Azkaban', 'J.K. Rowling', 'Harry Potter', 3, 'Fantasy', 'YA', 2.50, 'Like New', 2, '9780439136358',
             'A dangerous prisoner has escaped from Azkaban and seems to be coming after Harry.'),
            ('Harry Potter and the Goblet of Fire', 'J.K. Rowling', 'Harry Potter', 4, 'Fantasy', 'YA', 2.75, 'Very Good', 1, '9780439139595',
             'Harry is unexpectedly entered into the deadly Triwizard Tournament with lethal consequences.'),
            ('The Hunger Games', 'Suzanne Collins', 'The Hunger Games', 1, 'Dystopian/Adventure', 'YA', 2.25, 'Very Good', 2, '9780439023481',
             'In a dystopian future, 16-year-old Katniss volunteers to fight to the death in a televised arena.'),
            ('Catching Fire', 'Suzanne Collins', 'The Hunger Games', 2, 'Dystopian/Adventure', 'YA', 2.25, 'Like New', 1, '9780439023498',
             'Katniss returns to the arena as a victor in a shocking and deadly twist to the Hunger Games.'),
            ('Mockingjay', 'Suzanne Collins', 'The Hunger Games', 3, 'Dystopian/Adventure', 'YA', 2.00, 'Good', 2, '9780439023511',
             'Katniss becomes the face of rebellion in the final all-out battle against the Capitol.'),
            ('The Maze Runner', 'James Dashner', 'The Maze Runner', 1, 'Dystopian/Sci-Fi', 'YA', 2.00, 'Very Good', 1, '9780385737951',
             'A boy wakes up with no memory in a glade surrounded by a deadly maze he must find a way to escape.'),
            ('Divergent', 'Veronica Roth', 'Divergent', 1, 'Dystopian/Adventure', 'YA', 2.25, 'Like New', 1, '9780062024022',
             'In a future Chicago, Tris discovers she is Divergent — a dangerous secret in a society divided by factions.'),

            # ── Adult ─────────────────────────────────────────────────────────
            ('The Notebook', 'Nicholas Sparks', None, None, 'Romance', 'Adult', 2.00, 'Good', 2, '9780446605236',
             'An old man reads the story of a young couple\'s timeless love to a woman with dementia — a heartbreaking and beautiful tale.'),
            ('A Walk to Remember', 'Nicholas Sparks', None, None, 'Romance', 'Adult', 2.00, 'Very Good', 1, '9780446608954',
             'A rebellious teen falls in love with the quiet minister\'s daughter and is changed forever.'),
            ('The Lucky One', 'Nicholas Sparks', None, None, 'Romance', 'Adult', 2.00, 'Like New', 1, '9780446547574',
             'A Marine believes a photo of a woman he has never met saved his life in Iraq — and sets out to find her.'),
            ('Murder on the Orient Express', 'Agatha Christie', 'Hercule Poirot', None, 'Mystery', 'Adult', 2.50, 'Like New', 1, '9780062073501',
             'Hercule Poirot investigates a murder on a snowbound luxury train — every single passenger has a motive.'),
            ('And Then There Were None', 'Agatha Christie', None, None, 'Mystery/Thriller', 'Adult', 2.50, 'Very Good', 2, '9780062073471',
             'Ten strangers are lured to an isolated island and begin dying one by one — a perfect locked-room mystery.'),
            ('Death on the Nile', 'Agatha Christie', 'Hercule Poirot', None, 'Mystery', 'Adult', 2.25, 'Good', 1, '9780062073587',
             'Hercule Poirot investigates the murder of a beautiful heiress on an Egyptian Nile cruise.'),
            ('The Firm', 'John Grisham', None, None, 'Legal Thriller', 'Adult', 2.00, 'Good', 2, '9780440245926',
             'A young Harvard law grad discovers his prestigious new firm has deep ties to the mob — and no one gets out alive.'),
            ('A Time to Kill', 'John Grisham', None, None, 'Legal Thriller', 'Adult', 2.25, 'Very Good', 1, '9780385339667',
             'A Black father in Mississippi kills the men who raped his daughter — his lawyer must now convince an all-white jury.'),
            ('The Pelican Brief', 'John Grisham', None, None, 'Legal Thriller', 'Adult', 2.00, 'Good', 1, '9780440214823',
             "A law student's brief explaining the assassination of two Supreme Court justices puts her life in mortal danger."),
            ('Along Came a Spider', 'James Patterson', 'Alex Cross', 1, 'Crime Thriller', 'Adult', 2.00, 'Very Good', 2, '9780446364218',
             'Detective Alex Cross investigates a terrifying kidnapping that spirals into something far more sinister.'),
            ('Kiss the Girls', 'James Patterson', 'Alex Cross', 2, 'Crime Thriller', 'Adult', 2.00, 'Good', 1, '9780446364225',
             'Alex Cross hunts a serial kidnapper who is collecting young women — and his own niece is one of them.'),
            ('The Hunt for Red October', 'Tom Clancy', 'Jack Ryan', 1, 'Spy Thriller', 'Adult', 2.50, 'Very Good', 1, '9780870212857',
             'A brilliant Soviet submarine commander makes a daring race to defect to the United States.'),
            ('Patriot Games', 'Tom Clancy', 'Jack Ryan', 2, 'Spy Thriller', 'Adult', 2.25, 'Good', 1, '9780425132722',
             'CIA analyst Jack Ryan foils a terrorist attack on the British royal family — and becomes their next target.'),
            ('Killing Floor', 'Lee Child', 'Jack Reacher', 1, 'Crime Thriller', 'Adult', 2.25, 'Like New', 1, '9780515153651',
             'Jack Reacher wanders into a small Georgia town and is immediately arrested for a murder he did not commit.'),
            ('Die Trying', 'Lee Child', 'Jack Reacher', 2, 'Crime Thriller', 'Adult', 2.00, 'Very Good', 1, '9780515126426',
             'Reacher is kidnapped alongside an FBI agent and must use every instinct to survive.'),
            ('The Pillars of the Earth', 'Ken Follett', 'Kingsbridge', 1, 'Historical Fiction', 'Adult', 2.50, 'Good', 1, '9780452282179',
             'An epic 12th-century saga of building a cathedral, full of ambition, love, betrayal, and political intrigue.'),
            ('The Alchemist', 'Paulo Coelho', None, None, 'Literary Fiction', 'Adult', 2.00, 'Like New', 2, '9780062315007',
             'A young shepherd journeys from Spain to the Egyptian pyramids, discovering the secret of life along the way.'),
            ('Where the Crawdads Sing', 'Delia Owens', None, None, 'Literary Fiction', 'Adult', 2.50, 'Very Good', 2, '9780735224292',
             'A young woman raised alone in the North Carolina marshes becomes the prime suspect in a murder mystery.'),
            ('Educated', 'Tara Westover', None, None, 'Memoir', 'Adult', 2.50, 'Like New', 1, '9780399590504',
             'A woman raised in a survivalist family without schooling educates herself and earns a PhD from Cambridge.'),
            ('The Woman in the Window', 'A.J. Finn', None, None, 'Psychological Thriller', 'Adult', 2.00, 'Very Good', 1, '9780062678416',
             'An agoraphobic woman thinks she witnesses a crime from her window — but no one believes a word she says.'),
        ]

        for (title, author, series, series_num, genre, age_group, price,
             condition, quantity, isbn, description) in books:
            b = FoplBook(
                _title=title, _author=author, _series=series,
                _series_num=series_num, _genre=genre, _age_group=age_group,
                _price=price, _condition=condition, _quantity=quantity,
                _isbn=isbn, _description=description,
            )
            db.session.add(b)
        db.session.commit()
        print(f'Seeded {len(books)} FOPL books.')
