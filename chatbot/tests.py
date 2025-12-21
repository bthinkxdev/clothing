from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal
from app.models import Product, ProductVariant, Category, Order, Address, Inventory, Cart, CartItem
from chatbot.services import IntentParser, OrderTrackingHandler, ProductSearchHandler, SizeRecommendationHandler
from chatbot.models import ChatMessage, ChatSession
import json

User = get_user_model()

class IntentParserTests(TestCase):
    def setUp(self):
        self.parser = IntentParser()

    def test_track_order_intent(self):
        self.assertEqual(self.parser.parse("track order")[0], "track_order")
        self.assertEqual(self.parser.parse("where is my order")[0], "track_order")
        self.assertEqual(self.parser.parse("order status")[0], "track_order")
        
        # Test with order ID
        intent, data = self.parser.parse("order #12345")
        self.assertEqual(intent, "track_order")
        self.assertEqual(data['matched'][0], "12345")

    def test_find_product_intent(self):
        self.assertEqual(self.parser.parse("show products")[0], "find_product")
        self.assertEqual(self.parser.parse("looking for shoes")[0], "find_product")

    def test_find_by_size_intent(self):
        intent, data = self.parser.parse("do you have size XL")
        self.assertEqual(intent, "find_by_size")
        self.assertEqual(data['matched'][0].lower(), "xl")

    def test_find_by_color_intent(self):
        intent, data = self.parser.parse("available in red")
        self.assertEqual(intent, "find_by_color")
        self.assertTrue("red" in data['matched'])

    def test_price_check_intent(self):
        intent, data = self.parser.parse("under 500")
        self.assertEqual(intent, "price_check")
        self.assertEqual(data['matched'][0], "500")

    def test_size_recommendation_intent(self):
        self.assertEqual(self.parser.parse("what size should i buy")[0], "size_recommendation")

    def test_general_intent(self):
        self.assertEqual(self.parser.parse("hello")[0], "general")


class OrderTrackingHandlerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="password")
        self.address = Address.objects.create(
            user=self.user, full_name="Test User", line1="123 St", city="City", state="State", postal_code="12345"
        )
        self.category = Category.objects.create(name="Test Category", slug="test-category")
        self.product = Product.objects.create(name="Test Product", slug="test-product", category=self.category)
        self.variant = ProductVariant.objects.create(product=self.product, sku="TP-001", price=Decimal("100.00"), mrp=Decimal("120.00"))
        
        self.order = Order.objects.create(
            user=self.user, address=self.address, total=Decimal("100.00")
        )
        self.handler = OrderTrackingHandler()

    def test_track_specific_order_success(self):
        response = self.handler.handle(self.user, f"order {str(self.order.id)}", {})
        # Updated assertion to match actual response format "**Order #ID**"
        self.assertIn(f"Order #{str(self.order.id)[:8].upper()}", response['reply'])

    def test_track_specific_order_not_found(self):
        response = self.handler.handle(self.user, "order 999999", {})
        self.assertIn("Here are your recent orders", response['reply'])

    def test_track_recent_orders(self):
        response = self.handler.handle(self.user, "track my order", {})
        self.assertIn("Here are your recent orders", response['reply'])
        self.assertEqual(len(response['orders']), 1)
        self.assertEqual(response['orders'][0]['id'], str(self.order.id)[:8].upper())


class ProductSearchHandlerTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Shirts", slug="shirts")
        self.product1 = Product.objects.create(name="Blue Shirt", slug="blue-shirt", category=self.category, description="Cotton blue shirt")
        self.variant1 = ProductVariant.objects.create(product=self.product1, sku="BS-S", size="S", color="Blue", price=Decimal("500.00"), mrp=Decimal("600.00"))
        
        self.product2 = Product.objects.create(name="Red Shirt", slug="red-shirt", category=self.category)
        self.variant2 = ProductVariant.objects.create(product=self.product2, sku="RS-L", size="L", color="Red", price=Decimal("1000.00"), mrp=Decimal("1200.00"))
        
        self.handler = ProductSearchHandler()

    def test_search_by_keyword(self):
        response = self.handler.handle("looking for blue", {})
        self.assertIn("found 1 product", response['reply'])
        self.assertEqual(response['products'][0]['name'], "Blue Shirt")

    def test_filter_by_size(self):
        response = self.handler.handle("have size S", {}, filters={'size': 'S'})
        self.assertIn("found 1 product", response['reply'])
        self.assertEqual(response['products'][0]['name'], "Blue Shirt")

    def test_filter_by_color(self):
        response = self.handler.handle("have red", {}, filters={'color': 'Red'})
        self.assertIn("found 1 product", response['reply'])
        self.assertEqual(response['products'][0]['name'], "Red Shirt")

    def test_filter_by_price(self):
        response = self.handler.handle("under 600", {}, filters={'max_price': Decimal("600")})
        self.assertIn("found 1 product", response['reply'])
        self.assertEqual(response['products'][0]['name'], "Blue Shirt")


class SizeRecommendationHandlerTests(TestCase):
    def setUp(self):
        self.handler = SizeRecommendationHandler()
    
    def test_calculate_size_metric(self):
        state = {'height': '180', 'height_unit': 'cm', 'weight': '75', 'weight_unit': 'kg'}
        response = self.handler.handle("session", "msg", state)
        self.assertEqual(response['recommended_size'], 'M')

    def test_missing_height(self):
        state = {'weight': '75', 'weight_unit': 'kg'}
        response = self.handler.handle("session", "msg", state)
        self.assertIn("need your height", response['reply'])

    def test_missing_weight(self):
        state = {'height': '180', 'height_unit': 'cm'}
        response = self.handler.handle("session", "msg", state)
        self.assertIn("what's your weight", response['reply'])


class ChatbotAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('chatbot:ask')
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="password")

    def test_post_message_anonymous(self):
        response = self.client.post(self.url, json.dumps({'message': 'hello'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('reply', data)

    def test_post_message_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, json.dumps({'message': 'my orders'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ChatSession.objects.exists())
        self.assertTrue(ChatMessage.objects.filter(user=self.user).exists())

    def test_empty_message(self):
        response = self.client.post(self.url, json.dumps({'message': ''}), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_invalid_json(self):
        response = self.client.post(self.url, "not json", content_type='application/json')
        self.assertEqual(response.status_code, 400)
