/*
app.js

Этот скрипт управляет логикой мини-магазина внутри Telegram WebApp.

Функции:
- Инициализирует Telegram WebApp API и разворачивает окно.
- Хранит ассортимент товаров (две категории: "Сухофрукты" и "Орехи").
- Рендерит список товаров по выбранной категории.
- Позволяет пользователю увеличивать/уменьшать количество каждого товара.
- Подсчитывает количество товаров и общую сумму заказа.
- При нажатии "Перейти к оплате" формирует объект заказа и отправляет его боту
  через window.Telegram.WebApp.sendData(...).
*/

const tg = window.Telegram.WebApp;
tg.expand();
tg.ready();

const products = [
  // Сухофрукты
  { 
    id: "dried_apricots",
    cat: "dried",
    name: "Курага",
    price: 150,
    image: "https://sunnyfruit.uz/wp-content/uploads/2023/07/kuraga-subhona-2.jpg"
  },
  { 
    id: "prunes",
    cat: "dried",
    name: "Чернослив",
    price: 130,
    image: "https://abrakadabra.fun/uploads/posts/2022-02/1645979388_18-abrakadabra-fun-p-chernosliv-bez-kostochki-19.jpg"
  },

  // Орехи
  { 
    id: "walnuts",
    cat: "nuts",
    name: "Грецкий орех",
    price: 200,
    image: "https://static.insales-cdn.com/images/products/1/269/528622885/grecki.jpg"
  },
  { 
    id: "almonds",
    cat: "nuts",
    name: "Миндаль",
    price: 260,
    image: "https://chefsmandala.com/wp-content/uploads/2018/02/Almond.jpg"
  },
];


// корзина: {id: {id, name, price, qty}}
const cart = {};

let currentCategory = "dried";

const productsContainer = document.getElementById("products");
const cartCountEl = document.getElementById("cart-count");
const cartTotalEl = document.getElementById("cart-total");
const checkoutBtn = document.getElementById("checkout");

// переключение вкладок
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document
      .querySelectorAll(".tab")
      .forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    currentCategory = tab.dataset.cat;
    renderProducts();
  });
});

function renderProducts() {
  productsContainer.innerHTML = "";
  const filtered = products.filter((p) => p.cat === currentCategory);

  filtered.forEach((product) => {
    const card = document.createElement("div");
    card.className = "card";

    const left = document.createElement("div");

    const img = document.createElement("img");
    img.src = product.image;
    img.style.width = "70px";
    img.style.height = "70px";
    img.style.objectFit = "cover";
    img.style.borderRadius = "10px";
    img.style.marginBottom = "6px";

    const title = document.createElement("div");
    title.className = "card-title";
    title.textContent = product.name;

    const price = document.createElement("div");
    price.className = "card-price";
    price.textContent = `${product.price} грн / 100 г`;

    left.appendChild(img);
    left.appendChild(title);
    left.appendChild(price);

    const right = document.createElement("div");
    right.className = "qty-control";

    const minus = document.createElement("button");
    minus.className = "btn-round";
    minus.textContent = "−";

    const qtyValue = document.createElement("div");
    qtyValue.className = "qty-value";
    qtyValue.textContent = getQty(product.id);

    const plus = document.createElement("button");
    plus.className = "btn-round";
    plus.textContent = "+";

    minus.addEventListener("click", () => changeQty(product, -1, qtyValue));
    plus.addEventListener("click", () => changeQty(product, +1, qtyValue));

    right.appendChild(minus);
    right.appendChild(qtyValue);
    right.appendChild(plus);

    card.appendChild(left);
    card.appendChild(right);

    productsContainer.appendChild(card);
  });
}


function getQty(id) {
  return cart[id]?.qty || 0;
}

function changeQty(product, delta, qtyEl) {
  const id = product.id;
  const current = cart[id]?.qty || 0;
  let next = current + delta;
  if (next < 0) next = 0;

  if (next === 0) {
    delete cart[id];
  } else {
    cart[id] = {
      id: product.id,
      name: product.name,
      price: product.price,
      qty: next,
    };
  }

  qtyEl.textContent = next;
  recalcCart();
}

function recalcCart() {
  let count = 0;
  let total = 0;

  Object.values(cart).forEach((item) => {
    count += item.qty;
    total += item.qty * item.price;
  });

  cartCountEl.textContent = count;
  cartTotalEl.textContent = total;
}

// отправка заказа боту
checkoutBtn.addEventListener("click", () => {
  const items = Object.values(cart);

  if (items.length === 0) {
    alert("Корзина пуста. Добавь хотя бы один товар 🙂");
    return;
  }

  const order = {
    items: items.map((i) => ({
      id: i.id,
      name: i.name,
      qty: i.qty,
    })),
  };

  // Отправляем данные боту и закрываем WebApp
  tg.sendData(JSON.stringify(order));
  tg.close();
});

// первичная отрисовка
renderProducts();
recalcCart();
