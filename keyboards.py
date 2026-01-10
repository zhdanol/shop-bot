from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
import database as db

def main_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text='Каталог')
    builder.button(text='🛒 Корзина')
    builder.button(text='Мои заказы')
    builder.button(text='👤 Профиль')
    builder.button(text='ℹ️ Помощь')
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)

async def categories_menu():
    categories = await db.get_categories()
    builder = InlineKeyboardBuilder()
    
    for category_id, category_name in categories:
        builder.button(
            text=category_name,
            callback_data=f'category_{category_id}'
        )
        
    builder.button(text='🔙 Назад', callback_data='back_to_main')
    builder.adjust(2)
    return builder.as_markup()

async def products_menu(category_id: int):
    products = await db.get_products_by_category(category_id)
    builder = InlineKeyboardBuilder()
    
    for product in products:
        product_id, name, price, stock, _ = product
        text = f'{name} - {price} - ({stock} шт.)'
        builder.button(
            text=text,
            callback_data=f'product_{product_id}'
        )
    
    builder.button(text='🔙 Назад к категориям', callback_data='back_to_categories')
    builder.adjust(1)
    return builder.as_markup()

def product_menu(product_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text='➕ Добавить в корзину', callback_data=f'add_to_cart_{product_id}')
    builder.button(text='➖ Убрать из корзины', callback_data=f'remove_from_cart_{product_id}')
    builder.button(text='🔙 Назад', callback_data='back_to_products')
    builder.adjust(1)
    return builder.as_markup()

async def cart_menu(user_id: int):
    cart_items = await db.get_cart(user_id)
    builder = InlineKeyboardBuilder()
    
    for item in cart_items:
        cart_item_id, name, price, quantity, product_id = item
        builder.button(
            text=f'✏️ {name} (x{quantity})',
            callback_data=f'edit_cart_{cart_item_id}'
        )
    
    if cart_items:
        builder.button(text='✅ Оформить заказ', callback_data='checkout')
        builder.button(text='🗑️ Очистить корзину', callback_data='clear_cart')
        
    builder.button(text='🛒 Продолжить покупки', callback_data='back_to_categories')
    builder.adjust(1)
    return builder.as_markup()

def quantity_menu(cart_item_id: int, current_qty: int):
    builder = InlineKeyboardBuilder()
    builder.button(text='➖', callback_data=f'decrease_{cart_item_id}')
    builder.button(text=f'{current_qty}', callback_data=f'show_qty_{cart_item_id}')
    builder.button(text='➕', callback_data=f'increase_{cart_item_id}')
    builder.button(text='🗑️ Удалить', callback_data=f'delete_{cart_item_id}')
    builder.button(text='🔙 Назад', callback_data=f'back_to_cart')
    builder.adjust(3, 1, 1)
    return builder.as_markup()

def checkout_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ Подтвердить заказ', callback_data='confirm_order')
    builder.button(text='✏️ Изменить данные', callback_data='edit_profile')
    builder.button(text='❌ Отменить', callback_data='back_to_cart')
    builder.adjust(1)
    return builder.as_markup()

def admin_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text='📊 Статистика', callback_data='admin_stats')
    builder.button(text='📦 Заказы', callback_data='admin_orders')
    builder.button(text='➕ Добавить товар', callback_data='admin_add_product')
    builder.button(text='🏷️ Добавить категорию', callback_data='admin_add_category')
    builder.adjust(2)
    return builder.as_markup()
    