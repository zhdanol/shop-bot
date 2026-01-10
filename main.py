import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database as db
import keyboards as kb
from config import BOT_TOKEN, ID_ADMIN
import aiosqlite
logging.basicConfig(level=logging.INFO)


bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class OrderStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_address = State()
    
class AdminState(StatesGroup):
    waiting_for_category_name = State()
    waiting_for_category_desc = State()
    waiting_for_product_name = State()
    waiting_for_product_desc = State()
    waiting_for_product_price = State()
    waiting_for_product_stock = State()

@dp.message(Command('start'))
async def start_comand(message: types.Message):
    user = await db.get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    
    welcome_text = (
        'Добро можаловать в мой магазин!\n\n'
        'Вы можете\n'
        'Просматривать каталог товаров\n'
        'Добавлять товары в корзину\n'
        'Оформлять заказы\n'
        'Отслеживать статусы заказов\n\n'
        'Используйте кнопки ниже для навигации:'
    )
    
    await message.answer(welcome_text, reply_markup=kb.main_menu())

@dp.message(F.text == 'Каталог')
async def show_categories(message: types.Message):
    categories = await db.get_categories()
    if not categories:
        await message.answer('Категории пока пусты. Загляните позже!')
        return
    
    keyboard = await kb.categories_menu()
    await message.answer('📂 Выберите категорию:', reply_markup=keyboard)

@dp.message(F.text == '🛒 Корзина')
async def show_cart(message: types.Message):
    cart_items = await db.get_cart(message.from_user.id)
    
    if not cart_items:
        await message.answer('🛒 Ваша корзина пуста')
        return
    
    cart_text = '🛒 Ваша корзина:\n\n'
    total = 0
    
    for item in cart_items:
        _, name, price, quantity, _ = item
        item_total = price *quantity
        cart_text += f' {name}\n {price} {quantity} = {item_total}\n'
        total += item_total
    
    cart_text += f'\n💰 Итого: {total}'
    
    keyboard = await kb.cart_menu(message.from_user.id)
    await message.answer(cart_text, reply_markup=keyboard)

@dp.message(F.text == 'Мои заказы')
async def show_orders(message: types.Message):
    orders = await db.get_user_orders(message.from_user.id)
    
    if not orders:
        await message.answer('📦 У вас пока нет заказов')
        return
    
    orders_text = '📦 Ваши заказы:\n\n'
    for order in orders:
        order_id, total, status, created_at = order
        status_icons = {
            'pending': '⏳',
            'processing': '🔄',
            'shipped': '🚚',
            'delivered': '✅',
            'cancelled': '❌'
        }
        icon = status_icons.get(status, '📦')
        orders_text += f'{icon} Заказ #{order_id}\n'
        orders_text += f'   Сумма: {total}\n'
        orders_text += f'   Статус: {status}\n'
        orders_text += f'   Дата: {created_at}\n\n'
        
    await message.answer(orders_text)

@dp.message(F.text == '👤 Профиль')
async def show_profile(message: types.Message):
    user = await db.get_or_create_user(message.from_user.id)
    
    profile_text = (
        f'👤 Ваш профиль:\n\n'
        f'🆔 ID: {user[1]}\n'
        f'👤 Имя: {user[3] or 'Не указано'}\n'
        f'📱 Телефон: {user[4] or 'Не указан'}\n'
        f'🏠 Адрес: {user[5] or 'Не указан'}\n\n'
        f'📅 Регистрация: {user[7][:10] if user[7] else "Неизвестно"}'
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text='✏️ Редактировать профиль', callback_data='edit_profile')
    await message.answer(profile_text, reply_markup=builder.as_markup())
    
@dp.message(F.text == 'ℹ️ Помощь')
async def show_help(message: types.Message):
    help_text = (
        "❓ Помощь по боту:\n\n"
        "🛒 <b>Как сделать заказ:</b>\n"
        "1. Нажмите 'Каталог'\n"
        "2. Выберите категорию\n"
        "3. Выберите товар\n"
        "4. Добавьте в корзину\n"
        "5. Перейдите в корзину\n"
        "6. Оформите заказ\n\n"
        "📞 <b>Контакты:</b>\n"
        "Телефон: +7 (999) 123-45-67\n"
        "Email: shop@example.com\n"
        "График работы: 9:00-21:00\n\n"
        "📦 <b>Доставка:</b>\n"
        " Курьером - 300₽\n"
        " Самовывоз - бесплатно\n"
        " Почта России - 200₽\n\n"
        "💳 <b>Оплата:</b>\n"
        " Наличными при получении\n"
        " Картой онлайн\n"
        " Переводом на карту"
    )
    await message.answer(help_text, parse_mode='HTML')

@dp.callback_query(F.data.startswith('category_'))
async def show_products(callback: types.CallbackQuery):
    category_id = int(callback.data.split('_')[1])
    keyboard = await kb.products_menu(category_id)
    await callback.message.edit_text('🛍️ Выберите товар:', reply_markup=keyboard)
    await callback.answer()
    
@dp.callback_query(F.data.startswith('product_'))
async def show_product(callback: types.CallbackQuery):
    product_id = int(callback.data.split('_')[1])
    product = await db.get_product(product_id)
    
    if not product:
        await callback.answer('Товары не найдены')
        return
    
    product_text = (
        f'<b>{product[2]}</b>\n\n'
        f'📝 Описание: {product[3] or "Нет описания"}\n'
        f'💰 Цена: {product[4]}\n'
        f'📦 В наличии: {product[5]} шт.\n\n'
        f'🛒 Выберите действие:'
    )
    
    keyboard = kb.product_menu(product_id)
    await callback.message.edit_text(product_text, reply_markup=keyboard, parse_mode='HTML')
    await callback.answer()
    
@dp.callback_query(F.data.startswith('add_to_cart_'))
async def add_to_cart_handler(callback: types.CallbackQuery):
    product_id = int(callback.data.split('_')[3])
    await db.add_to_cart(callback.from_user.id, product_id)
    await callback.answer('✅ Товар добавлен в корзину!')

@dp.callback_query(F.data == 'back_to_categories')
async def back_to_categories(callback: types.CallbackQuery):
    keyboard = await kb.categories_menu()
    await callback.message.edit_text('📂 Выберите категорию:', reply_markup=keyboard)
    await callback.answer()
    
@dp.callback_query(F.data.startswith('back_to_cart'))
async def back_to_cart(callback: types.CallbackQuery):
    cart_items = await db.get_cart(callback.from_user.id)
    
    if not cart_items:
        await callback.message.edit_text('🛒 Ваша корзина пуста')
        return
    cart_text = '🛒 Ваша корзина:\n\n'
    total = 0
    
    for item in cart_items:
        _, name, price, quantity, _ = item
        item_total = price * quantity
        cart_text += f'{name}\n {price} * {quantity} = {item_total}\n'
        total += item_total
    cart_text += f'\n 💰 Итого:  {total}'
    
    keyboard = await kb.cart_menu(callback.from_user.id)
    await callback.message.edit_text(cart_text, reply_markup=keyboard)
    await callback.answer()
@dp.callback_query(F.data == 'checkout')
async def start_checkout(callback: types.CallbackQuery, state: FSMContext):
    user = await db.get_or_create_user(callback.from_user.id)
    
    if not user[4] or not user[5]:
        await callback.message.answer(
            '📝 Для оформления заказа нужны ваши контактные данные.\n'
            'Пожалуйста, укажите ваш номер телефона:'
        )
        await callback.answer()
        
        await state.set_state(OrderStates.waiting_for_phone)
        return
    
    cart_items = await db.get_cart(callback.from_user.id)
    total = sum(item[2] * item[3] for item in cart_items)
    
    confirm_text = (
        '✅ Подтвердите заказ:\n\n'
        f'📱 Телефон: {user[4]}\n'
        f'🏠 Адрес: {user[5]}\n\n'
        f'🛒 Товаров: {len(cart_items)}\n'
        f'💰 Итого: {total}\n\n'
        'Верно ли все указано?'
    )
    
    keyboard = kb.checkout_menu()
    await callback.message.edit_text(confirm_text, reply_markup=keyboard)
    await callback.answer()

@dp.message(OrderStates.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    
    if len(phone) != 11:
        await message.answer('❌ Пожалуйста, введите корректный номер телефона:')
        return
    
    await db.update_user_info(message.from_user.id, phone=phone)
    
    await state.set_state(OrderStates.waiting_for_address)
    await message.answer('📝 Отлично! Теперь укажите ваш адрес доставки:')

@dp.message(OrderStates.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    address = message.text.strip()
    
    if len(address) < 5:
        await message.answer('❌ Адрес слишком короткий. Введите полный адрес:')
        return
    
    await db.update_user_info(message.from_user.id, address=address)
    
    await state.clear()
    
    user = await db.get_or_create_user(message.from_user.id)
    cart_items = await db.get_cart(message.from_user.id)
    total = sum(item[2] * item[3] for item in cart_items)
    
    confirm_text = (
        '✅ Подтвердите заказ:\n\n'
        f'📱 Телефон: {user[4]}\n'
        f'🏠 Адрес: {user[5]}\n\n'
        f'🛒 Товаров: {len(cart_items)}\n'
        f'💰 Итого: {total}\n\n'
        'Верно ли все указано?'
    )
    
    keyboard = kb.checkout_menu()
    await message.answer(confirm_text, reply_markup=keyboard)
    
@dp.callback_query(F.data == 'confirm_order')
async def confirm_order(callback: types.CallbackQuery):
    user = await db.get_or_create_user(callback.from_user.id)
    
    if not user[4] or not user[5]:
        await callback.answer('❌ Не заполнены контактные данные')
        return
    
    order_id = await db.create_order(callback.from_user.id, user[4], user[5])
    
    if order_id:
        await callback.message.edit_text(
            f"🎉 Заказ #{order_id} оформлен!\n\n"
            "Наш менеджер свяжется с вами в ближайшее время для подтверждения.\n"
            "Статус заказа можно отслеживать в разделе 'Мои заказы'."
        )
    else:
        await callback.message.edit_text('❌ Не удалось оформить заказ. Корзина пуста.')
        
    await callback.answer()
    
@dp.callback_query(F.data.startswith('edit_cart_'))
async def edit_cart_item(callback: types.CallbackQuery):
    cart_item_id = int(callback.data.split('_')[2])
    cart_items = await db.get_cart(callback.from_user.id)
    
    for item in cart_items:
        if item[0] == cart_item_id:
            keyboard = kb.quantity_menu(cart_item_id, item[3])
            await callback.message.edit_text(
                f'✏️ Редактирование: {item[1]}\n'
                f'Текущее количество: {item[3]}\n',
                reply_markup=keyboard
            )
            break
    await callback.answer()

@dp.callback_query(F.data.startswith('increase_'))
async def increase_quantity(callback: types.CallbackQuery):
    cart_item_id = int(callback.data.split('_')[1])
    cart_items = await db.get_cart(callback.from_user.id)
    
    for item in cart_items:
        if item[0] == cart_item_id:
            new_qty = item[3] + 1
            await db.update_cart_item(cart_item_id, new_qty)
            
            keyboard = kb.quantity_menu(cart_item_id, new_qty)
            await callback.message.edit_text(
               f'✏️ Редактирование: {item[1]}\n'
               f'Текущее количество: {new_qty}',
               reply_markup=keyboard
            )
            break
    await callback.answer()
    
@dp.callback_query(F.data.startswith('decrease_'))
async def decrease_quantity(callback: types.CallbackQuery):
    cart_item_id = int(callback.data.split('_')[1])
    cart_items = await db.get_cart(callback.from_user.id)
    
    for item in cart_items:
        if item[0] == cart_item_id:
            new_qty = item[3] - 1
            await db.update_cart_item(cart_item_id, new_qty)
            
            if new_qty <= 0:
                await callback.message.answer('✅ Товар удален из корзины')
                await asyncio.sleep(1)
                await back_to_cart(callback)
                return
            
            keyboard = kb.quantity_menu(cart_item_id, new_qty)
            await callback.message.edit_text(
               f'✏️ Редактирование: {item[1]}\n'
               f'Текущее количество: {new_qty}',
               reply_markup=keyboard
            )
            break
    await callback.answer()

@dp.callback_query(F.data == 'clear_cart')
async def clear_cart_handler(callback: types.CallbackQuery):
    await db.clear_cart(callback.from_user.id)
    await callback.message.edit_text('✅ Корзина очищена')
    await callback.answer()
    
@dp.callback_query(F.data.startswith('delete_'))
async def delete_cart_item(callback: types.CallbackQuery):
    cart_item_id = int(callback.data.split('_')[1])
    await db.update_cart_item(cart_item_id, 0)
    await callback.message.edit_text('✅ Товар удален из корзины')
    await callback.answer()
    
@dp.callback_query(F.data == 'back_to_main')
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.answer(
        'Главное меню:',
        reply_markup=kb.main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == 'back_to_products')
async def back_to_product(callback: types.CallbackQuery):
    keyboard = await kb.categories_menu()
    await callback.message.edit_text('📂 Выберите категорию:', reply_markup=keyboard)
    await callback.answer()
    
@dp.callback_query(F.data.startswith('remove_from_cart_'))
async def remove_from_cart(callback: types.CallbackQuery):
    product_id = int(callback.data.split('_')[3])
    cart_items = await db.get_cart(callback.from_user.id)
    for item in cart_items:
        if item[4] == product_id:
            await db.update_cart_item(item[0], 0)
            break
    await callback.answer('✅ Товар удален из корзины')

@dp.callback_query(F.data == 'back_to_profile')
async def back_to_profile_handler(callback: types.CallbackQuery):
    await show_profile(callback.message)
    await callback.answer
    
@dp.callback_query(F.data == 'edit_profile')
async def edit_profile(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text='📱 Изменить телефон', callback_data='change_phone')
    builder.button(text='🏠 Изменить адрес', callback_data='change_address')
    builder.button(text='🔙 Назад', callback_data='back_to_profile')
    builder.adjust(1)
    
    await callback.message.edit_text(
        '✏️ Что вы хотите изменить?',
        reply_markup=builder.as_markup()
    )
    await callback.answer()
    
@dp.message(Command('admin'))
async def admin_panel(message: types.Message):
    if message.from_user.id not in ID_ADMIN:
        await message.answer('⛔ У вас нет доступа к админ-панели')
        return
    await message.answer('👑 Админ-панель:', reply_markup=kb.admin_menu())

@dp.callback_query(F.data == 'admin_stats')
async def admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id not in ID_ADMIN:
        await callback.answer('⛔ Нет доступа')
        return
    
    total_orders = 0
    total_revenue = 0.0
    orders = await db.get_all_orders()
    
    if orders:
        total_orders = len(orders)
        total_revenue = sum(order[2] for order in orders)
    
    stats_text = (
        '📊 Статистика магазина:\n\n'
        f'📦 Всего заказов: {total_orders}\n'
        f'💰 Общая выручка: {total_revenue:.2f}\n'
        f'👤 Пользователей: {await get_user_count()}\n'
        f'🛍️ Товаров в каталоге: {await get_product_count()}'
    )
    
    await callback.message.answer(stats_text)
    await callback.answer()

@dp.callback_query(F.data == 'admin_add_product')
async def admin_add_product_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ID_ADMIN:
        await callback.answer('⛔ Нет доступа')
        return
    categories = await db.get_categories()
    if not categories:
        await callback.message.answer('❌ Сначала создайте категорию')
        return
    
    builder = InlineKeyboardBuilder()
    for category_id, category_name in categories:
        builder.button(text=category_name, callback_data=f'admin_select_category_{category_id}')
    builder.button(text='❌ Отмена', callback_data='admin_cancel')
    builder.adjust(1)
    
    await callback.message.answer('📂 Выберите категорию для нового товара:', reply_markup=builder.as_markup())
    await callback.answer()
    
@dp.callback_query(F.data == 'admin_add_category')
async def admin_add_category_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ID_ADMIN:
        await callback.answer('⛔ Нет доступа')
        return
    
    await state.set_state(AdminState.waiting_for_category_name)
    await callback.message.answer('📝 Введите название новой категории:')
    await callback.answer()

@dp.callback_query(F.data.startswith('admin_select_category_'))
async def admin_select_category(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ID_ADMIN:
        await callback.answer('⛔ Нет доступа')
        return
    
    category_id = int(callback.data.split('_')[3])
    await state.update_data(category_id=category_id)
    await callback.answer()

@dp.callback_query(F.data == 'admin_cancel')
async def admin_cansel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer('❌ Операция отменена')
    await callback.answer()

@dp.message(AdminState.waiting_for_category_name)
async def process_category_name(message: types.Message, state: FSMContext):
    await state.update_data(category_name=message.text)
    await state.set_state(AdminState.waiting_for_category_desc)
    await message.answer('📝 Введите описание категории (или отправьте "-" для пропуска):')

@dp.message(AdminState.waiting_for_category_desc)
async def process_category_desc(message: types.Message, state: FSMContext):
    data = await state.get_data()
    category_name = data['category_name']
    category_desc = message.text if message.text != '-' else ''
    
    await db.add_category(category_name, category_desc)
    await state.clear()
    await message.answer(f'✅ Категория "{category_name}" добавлена!')
    
@dp.message(AdminState.waiting_for_product_name)
async def process_product_name(message: types.Message, state: FSMContext):
    await state.update_data(product_name=message.text)
    await state.set_state(AdminState.waiting_for_product_desc)
    await message.answer('📝 Введите описание товара (или отправьте "-" для пропуска):')

@dp.message(AdminState.waiting_for_product_desc)
async def process_product_desc(message: types.Message, state: FSMContext):
    await state.update_data(product_desc=message.text if message.text != '-' else '')
    await state.set_state(AdminState.waiting_for_product_price)
    await message.answer('💰 Введите цену товара (только число, например: 1000.50):')

@dp.message(AdminState.waiting_for_product_price)
async def process_product_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(product_price=price)
        await state.set_state(AdminState.waiting_for_product_stock)
        await message.answer('📦 Введите количество товара на складе (только число):')
    except ValueError:
        await message.answer('❌ Неверный формат цены. Введите число:')
    
@dp.message(AdminState.waiting_for_product_stock)
async def process_product_stock(message: types.Message, state: FSMContext):
    try:
        stock = int(message.text)
        data = await state.get_data()
        
        await db.add_product(
            category_id=data['category_id'],
            name=data['product_name'],
            description=data['product_desc'],
            price=data['product_price'],
            stock=stock
        )
        
        await state.clear()
        await message.answer(f'✅ Товар "{data["product_name"]}" добавлен в категорию!')
    except ValueError:
        await message.answer('❌ Неверный формат количества. Введите целое число:')

async def get_user_count():
    from database import DB_PATH  # Импортируем здесь
    async with aiosqlite.connect(DB_PATH) as connection:  # Используем другое имя переменной
        async with connection.execute('SELECT COUNT(*) FROM users') as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

async def get_product_count():
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as connection:
        async with connection.execute('SELECT COUNT(*) FROM products') as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

async def get_order_count():
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as connection:
        async with connection.execute('SELECT COUNT(*) FROM orders') as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

async def get_total_revenue():
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as connection:
        async with connection.execute('SELECT SUM(total_amount) FROM orders') as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

@dp.callback_query(F.data == 'admin_orders')
async def admin_orders(callback: types.CallbackQuery):
    if callback.from_user.id not in ID_ADMIN:
        await callback.answer('⛔ Нет доступа')
        return
    
    orders = await db.get_all_orders()
    
    if not orders:
        await callback.message.answer('📦 Заказов пока нет')
        return
    
    orders_text = '📦 Все заказы:\n\n'
    for order in orders:
        order_id, name, total, status, created = order
        orders_text += f'#{order_id} - {name}\n'
        orders_text += f'   Сумма: {total} | Статус: {status}\n'
        orders_text += f'   Дата: {created[:10]}\n\n'
        
    await callback.message.answer(orders_text)
    await callback.answer()
    



async def main():
    await db.init_db()
    
    categories = await db.get_categories()
    if not categories:
        await db.add_category('Электроника', 'Смартфоны, ноутбуки, гаджеты')
        await db.add_category('Одежда', 'Мужская и женская одежда')
        await db.add_category('Транспорт', 'Автомобили')
        
        await db.add_product(1, 'Iphone 16 pro', 'Новый, запечатанный', 77000.00, 10)
        await db.add_product(2, 'Свитер', 'свитер yves saint laurent', 210900.00, 50)
        await db.add_product(3, 'BMW M3', 'Новая', 12000000.00,  5)

    print('Бот запущен......')
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        