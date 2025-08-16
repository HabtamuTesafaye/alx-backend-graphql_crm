import re
import graphene
from graphene_django import DjangoObjectType
from .models import Customer, Product, Order
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal
from datetime import datetime
from .filters import CustomerFilter, ProductFilter, OrderFilter
from graphene_django.filter import DjangoFilterConnectionField

class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        interfaces = (graphene.relay.Node,)  # Relay node for DjangoFilterConnectionField

class ProductType(DjangoObjectType):
    price = graphene.Float()  # Override to use Float instead of Decimal
    
    class Meta:
        model = Product
        interfaces = (graphene.relay.Node,)
        
    def resolve_price(self, info):
        return float(self.price)

class OrderType(DjangoObjectType):
    totalAmount = graphene.Float()
    orderDate = graphene.DateTime()
    products = graphene.List(ProductType)  # Override the default connection
    
    class Meta:
        model = Order
        # Remove relay interface to avoid connection issues
        # interfaces = (graphene.relay.Node,)
        
    def resolve_totalAmount(self, info):
        return float(self.total_amount)
        
    def resolve_orderDate(self, info):
        return self.order_date
        
    def resolve_products(self, info):
        return self.products.all()


# Define input types
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()

class CreateCustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()

class CreateProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Float(required=True)
    stock = graphene.Int()

class CreateOrderInput(graphene.InputObjectType):
    customerId = graphene.ID(required=True)
    productIds = graphene.List(graphene.ID, required=True)
    orderDate = graphene.DateTime()


# CreateCustomer Mutation
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CreateCustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    def mutate(self, info, input):
        if Customer.objects.filter(email=input.email).exists():
            raise ValidationError("Email already exists")

        if input.phone and not re.match(r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$', input.phone):
            raise ValidationError("Invalid phone number format")

        customer = Customer.objects.create(
            name=input.name,
            email=input.email,
            phone=input.phone
        )
        return CreateCustomer(customer=customer, message="Customer created successfully")


# BulkCreateCustomers Mutation
class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(graphene.NonNull(CustomerInput), required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    def mutate(self, info, input):
        created_customers = []
        errors = []

        with transaction.atomic():
            for data in input:
                try:
                    if Customer.objects.filter(email=data.email).exists():
                        errors.append(f"Email already exists: {data.email}")
                        continue

                    if data.phone and not re.match(r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$', data.phone):
                        errors.append(f"Invalid phone: {data.phone}")
                        continue

                    cust = Customer.objects.create(
                        name=data.name,
                        email=data.email,
                        phone=data.phone
                    )
                    created_customers.append(cust)

                except Exception as e:
                    errors.append(str(e))

        return BulkCreateCustomers(customers=created_customers, errors=errors)


# CreateProduct Mutation
class CreateProduct(graphene.Mutation):
    class Arguments:
        input = CreateProductInput(required=True)

    product = graphene.Field(ProductType)

    def mutate(self, info, input):
        if Decimal(input.price) <= 0:
            raise ValidationError("Price must be positive")
        if input.stock is not None and input.stock < 0:
            raise ValidationError("Stock cannot be negative")

        product = Product.objects.create(
            name=input.name,
            price=input.price,
            stock=input.stock if input.stock is not None else 0
        )
        return CreateProduct(product=product)


# CreateOrder Mutation
class CreateOrder(graphene.Mutation):
    class Arguments:
        input = CreateOrderInput(required=True)

    order = graphene.Field(OrderType)

    def mutate(self, info, input):
        try:
            customer = Customer.objects.get(id=input.customerId)
        except Customer.DoesNotExist:
            raise ValidationError("Invalid customer ID")

        products = Product.objects.filter(id__in=input.productIds)
        if not products.exists():
            raise ValidationError("No valid products found")
        if products.count() != len(input.productIds):
            raise ValidationError("Some product IDs are invalid")

        total_amount = sum(p.price for p in products)

        order = Order.objects.create(
            customer=customer,
            total_amount=total_amount,
            order_date=input.orderDate or datetime.now()
        )
        order.products.set(products)

        return CreateOrder(order=order)


# Query
class Query(graphene.ObjectType):
    all_customers = DjangoFilterConnectionField(CustomerType, filterset_class=CustomerFilter)
    all_products = DjangoFilterConnectionField(ProductType, filterset_class=ProductFilter)
    # Remove all_orders from connection field since OrderType doesn't have relay interface
    # all_orders = DjangoFilterConnectionField(OrderType, filterset_class=OrderFilter)

    # Keep your old simple lists as well if you want
    customers = graphene.List(CustomerType)
    products = graphene.List(ProductType)
    orders = graphene.List(OrderType)

    def resolve_customers(self, info):
        return Customer.objects.all()

    def resolve_products(self, info):
        return Product.objects.all()

    def resolve_orders(self, info):
        return Order.objects.all()

# Mutation
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()

