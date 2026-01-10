import sqlite3
import aiosqlite
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / 'shop.db'

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Категории
        await db.execute('''
            CREATE TABLE IF NOT EXISTS categories(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Товары
        await db.execute('''
            CREATE TABLE IF NOT EXISTS products(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                stock INTEGER DEFAULT 0,
                image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories (id)
            )
        ''')
        
         # Пользователи
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                address TEXT,
                is_admin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Корзина
        await db.execute('''
            CREATE TABLE IF NOT EXISTS cart(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')

        # Заказы
        await db.execute('''
            CREATE TABLE IF NOT EXISTS orders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                phone TEXT,
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Элементы заказа
        await db.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        await db.commit()
        print('База данных инициализирована')


# КАТЕГОРИИ        
async def get_categories():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT id, name FROM categories ORDER BY name') as cursor:
            return await cursor.fetchall()
        
async def add_category(name: str, description: str = ''):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO categories (name, description) VALUES (?, ?)',
            (name, description)
        )
        await db.commit()

# ТОВАРЫ
async def get_products_by_category(category_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT id, name, price, stock, image_path FROM products WHERE category_id = ?',
            (category_id,)
        ) as cursor:
            return await cursor.fetchall()
        
async def get_product(product_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT * FROM products WHERE id = ?',
            (product_id,)
        ) as cursor:
            return await cursor.fetchone()
        
async def add_product(category_id: int, name: str, description: str, price: float, stock: int, image_path: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            '''INSERT INTO products (category_id, name, description, price, stock, image_path)
                VALUES (?, ?, ?, ?, ?, ?)''',
            (category_id, name, description, price, stock, image_path)
        )
        await db.commit()

# ПОЛЬЗОВАТЕЛИ
async def get_or_create_user(user_id: int, username: str = None, full_name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT * FROM users WHERE user_id = ?',
            (user_id,)
        ) as cursor:
            user = await cursor.fetchone()
            
        if not user:
            await db.execute(
                'INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)',
                (user_id, username, full_name)
            )
            await db.commit()
            
            async with db.execute(
                'SELECT * FROM users WHERE user_id = ?',
                (user_id,)
            ) as cursor:
                user = await cursor.fetchone()
        
        return user

async def update_user_info(user_id: int, phone: str = None, address: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if phone:
            await db.execute(
                'UPDATE users SET phone = ? WHERE user_id = ?',
                (phone, user_id)
            )
        if address:
            await db.execute(
                'UPDATE users SET address = ? WHERE user_id = ?',
                (address, user_id)
            )
        await db.commit()
        
# КОРЗИНА
async def add_to_cart(user_id: int, product_id: int, quantity: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT id, quantity FROM cart WHERE user_id = ? AND product_id = ?',
            (user_id, product_id)
        ) as cursor:
            item = await cursor.fetchone()
            
        if item :
            new_quantity = item[1] + quantity
            await db.execute(
                'UPDATE cart SET quantity = ? WHERE id = ?',
                (new_quantity, item[0])
            )
        else:
            await db.execute(
                'INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)',
                (user_id, product_id, quantity)
            )
        await db.commit()
        
async def get_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT c.id, p.name, p.price, c.quantity, p.id as product_id
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = ?              
                ''', (user_id,)) as cursor:
            return await cursor.fetchall()

async def update_cart_item(cart_item_id: int, quantity: int):
    async with aiosqlite.connect(DB_PATH) as db:
        if quantity <= 0:
            await db.execute('DELETE FROM cart WHERE id = ?', (cart_item_id,))
        else:
            await db.execute(
                'UPDATE cart SET quantity = ? WHERE id = ?',
                (quantity, cart_item_id)
            )
        await db.commit()
        
async def clear_cart(user_id: int, db=None):
    if db:
        await db.execute('DELETE FROM cart WHERE user_id = ?', (user_id,))
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('DELETE FROM cart WHERE user_id = ?', (user_id,))
            await db.commit()

# ЗАКАЗЫ
async def get_cart_with_db(db, user_id: int):
    async with db.execute('''
        SELECT c.id, p.name, p.price, c.quantity, p.id as product_id
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = ?              
            ''', (user_id,)) as cursor:
        return await cursor.fetchall()

async def clear_cart_with_db(db, user_id: int):
    await db.execute('DELETE FROM cart WHERE user_id = ?', (user_id,))

async def create_order(user_id: int, phone: str, address: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cart_items = await get_cart_with_db(db, user_id)
        if not cart_items:
            return None
        
        total_amount = sum(item[2] * item[3] for item in cart_items)
        
        cursor = await db.execute(
            '''INSERT INTO orders (user_id, total_amount, phone, address)
            VALUES (?, ?, ?, ?)''',
            (user_id, total_amount, phone, address)
        )
        order_id = cursor.lastrowid
        
        for item in cart_items:
            await db.execute(
                '''INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (?, ?, ?, ?)''',
                (order_id, item[4], item[3], item[2])
            )
            
        await clear_cart_with_db(db, user_id)
        
        await db.commit()
        return order_id
    
async def get_user_orders(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT id, total_amount, status, created_at FROM orders WHERE user_id = ? ORDER BY created_at DESC',
            (user_id,)
        ) as cursor:
            return await cursor.fetchall()

# АДМИН
async def get_all_orders():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT o.id, u.full_name, o.total_amount, o.status, o.created_at
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            ORDER BY o.created_at DESC                
        ''') as cursor:
            return await cursor.fetchall()

async def update_order_status(order_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'UPDATE orders SET status = ? WHERE id = ?',
            (status, order_id)
        )
        await db.commit()
    