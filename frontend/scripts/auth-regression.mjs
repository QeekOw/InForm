import assert from "node:assert/strict";

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || "playwright");
const base = process.env.AUTH_TEST_URL || "http://localhost:3000";
const browser = await chromium.launch({ headless: true });
const account = {
  id: "auth-regression",
  email: "auth-regression@example.test",
  name: "Auth regression",
  created_at: "2026-11-07T00:00:00Z",
  date_of_birth: "1995-01-01",
  height_cm: 175,
  default_biological_sex: "male",
  default_activity_multiplier: 1.55,
  default_fitness_goal: "hypertrophy",
  token: "regression-token",
};
const profile = { age: 31, biological_sex: "male", activity_multiplier: 1.55, fitness_goal: "hypertrophy" };
const reading = {
  weight_kg: 80,
  lean_body_mass_kg: 64,
  percent_body_fat: 20,
  skeletal_muscle_mass_kg: 35,
  basal_metabolic_rate_kcal: 1752,
  segmental_lean: { left_arm_kg: 3.5, right_arm_kg: 3.5, left_leg_kg: 9, right_leg_kg: 9, trunk_kg: 28 },
  source_device: "inbody_270",
  visceral_fat_level: 5,
};
const plan = {
  nutrition: { bmr_kcal: 1752, tdee_kcal: 2716, target_calories_kcal: 3016, protein_g: 160, carbs_g: 392, fats_g: 90, fiber_g: 30 },
  exercises: { detected_imbalances: [], unconfirmed_imbalance_pairs: [], exercises: [] },
  narrative_text: "Regression fixture plan.",
  narrative_source: "fallback",
};

async function check(name, run) {
  const context = await browser.newContext();
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => {
    if (message.type() === "error" && /hydration|hydrated|React error #418/i.test(message.text())) errors.push(message.text());
  });
  await page.route("**/auth/login", route => route.fulfill({ json: account }));
  await page.route("**/auth/logout", route => route.fulfill({ json: { status: "ok" } }));
  await page.route("**/scans", route => route.fulfill({ json: [] }));
  await page.route("**/scans/current", route => route.fulfill({ status: 404, json: {} }));
  try {
    await run(page);
    assert.deepEqual(errors, [], "no browser runtime or hydration errors");
    console.log(`PASS ${name}`);
  } finally {
    await context.close();
  }
}

async function holdAuth(page, result) {
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  await page.route("**/auth/me", async route => {
    await gate;
    await route.fulfill({ status: result ? 200 : 401, json: result || { detail: "Not authenticated" } });
  });
  return async () => {
    const response = page.waitForResponse(response => new URL(response.url()).pathname === "/auth/me");
    release();
    await (await response).finished();
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  };
}

async function login(page, target = "/dashboard") {
  await page.getByLabel("Email Address").fill(account.email);
  await page.getByLabel("Password", { exact: true }).fill("regression-password");
  await page.getByRole("button", { name: "Log In", exact: true }).click();
  await page.waitForURL(`**${target}`);
}

async function seedResult(page, nextAfterAuth = null) {
  await page.addInitScript(({ reading, profile, nextAfterAuth }) => {
    sessionStorage.setItem("inform:reading", JSON.stringify(reading));
    sessionStorage.setItem("inform:profile", JSON.stringify(profile));
    if (nextAfterAuth) sessionStorage.setItem("inform:nextAfterAuth", JSON.stringify(nextAfterAuth));
  }, { reading, profile, nextAfterAuth });
  await page.route("**/plan", route => route.fulfill({ json: plan }));
}

try {
  await check("start and guest flow while auth is pending", async page => {
    await holdAuth(page, null);
    await page.goto(base);
    await page.getByRole("link", { name: "Get Started" }).click();
    await page.getByRole("link", { name: "Continue as a Guest" }).click();
    await page.waitForURL("**/upload");
  });

  await check("start remains usable when auth is unavailable", async page => {
    await page.route("**/auth/me", route => route.abort("failed"));
    await page.goto(base);
    await page.getByRole("link", { name: "Get Started" }).click();
    assert.equal(await page.getByRole("link", { name: "Continue as a Guest" }).getAttribute("href"), "/upload");
  });

  await check("pending start reaches dashboard when signed in", async page => {
    const release = await holdAuth(page, account);
    await page.goto(base);
    await page.getByRole("link", { name: "Get Started" }).click();
    await page.waitForURL("**/sign-in?start=1");
    await release();
    await page.waitForURL("**/dashboard");
  });

  await check("pending start preserves an explicit destination", async page => {
    const release = await holdAuth(page, account);
    await page.goto(`${base}/sign-in?start=1&redirect=/account`);
    await release();
    await page.waitForURL("**/account");
    await page.getByText(account.email, { exact: true }).waitFor();
  });

  await check("cached signed-in account direct navigation and reload hydrate", async page => {
    const release = await holdAuth(page, account);
    await page.addInitScript(account => {
      sessionStorage.setItem("inform:account", JSON.stringify(account));
      sessionStorage.setItem("inform:authToken", JSON.stringify(account.token));
    }, account);
    await page.goto(`${base}/account`);
    await page.getByText(account.email, { exact: true }).waitFor();
    await page.reload();
    await page.getByText(account.email, { exact: true }).waitFor();
    await release();
    await page.getByText(account.email, { exact: true }).waitFor();
  });

  await check("late guest probe cannot overwrite login", async page => {
    const release = await holdAuth(page, null);
    await page.goto(`${base}/sign-in`);
    await login(page);
    await release();
    assert.equal(new URL(page.url()).pathname, "/dashboard");
    assert.equal(await page.evaluate(() => JSON.parse(sessionStorage.getItem("inform:account"))?.email), account.email);
  });

  await check("pending start preserves a stored save destination after login", async page => {
    const release = await holdAuth(page, null);
    await seedResult(page, "/result?save=1");
    await page.route("**/scans", route => route.fulfill({ json: route.request().method() === "POST" ? {} : [] }));
    await page.goto(`${base}/sign-in?start=1`);
    await login(page, "/result?save=1");
    await page.getByRole("heading", { name: "Saved!", exact: true }).waitFor();
    await release();
    assert.equal(new URL(page.url()).pathname, "/result");
  });

  await check("guest signup returns to save the existing reading", async page => {
    const release = await holdAuth(page, null);
    await seedResult(page);
    let saved;
    await page.route("**/auth/signup", route => route.fulfill({ json: account }));
    await page.route("**/scans", route => {
      if (route.request().method() === "POST") saved = route.request().postDataJSON();
      return route.fulfill({ json: route.request().method() === "POST" ? {} : [] });
    });
    await page.goto(`${base}/result`);
    await page.getByRole("button", { name: "Save", exact: true }).click();
    await page.getByRole("link", { name: "Sign Up to Save", exact: true }).click();
    await page.getByLabel("Email Address").fill(account.email);
    await page.getByLabel("Password", { exact: true }).fill("regression-password");
    await page.getByLabel("Confirm Password", { exact: true }).fill("regression-password");
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await page.getByLabel("Date of Birth").fill(account.date_of_birth);
    await page.getByRole("button", { name: "Sign Up", exact: true }).click();
    await page.getByRole("heading", { name: "Saved!", exact: true }).waitFor();
    await release();
    assert.deepEqual(saved.inbody, reading, "signup preserves the guest reading");
    assert.deepEqual(saved.user, profile, "save retains the plan profile");
    assert.equal(await page.evaluate(() => JSON.parse(sessionStorage.getItem("inform:account"))?.email), account.email);
  });

  await check("late signed-in probe cannot restore a logged-out session", async page => {
    const release = await holdAuth(page, account);
    await page.goto(`${base}/sign-in`);
    await login(page);
    await page.getByRole("link", { name: "Your profile", exact: true }).click();
    await page.getByRole("button", { name: "Sign Out", exact: true }).click();
    await page.getByRole("button", { name: "Sign Out", exact: true }).last().click();
    await page.waitForURL(url => url.pathname !== "/account");
    await release();
    assert.equal(await page.evaluate(() => sessionStorage.getItem("inform:account")), null);
    await page.unroute("**/auth/me");
    await page.route("**/auth/me", route => route.fulfill({ status: 401, json: {} }));
    for (const path of ["/account", "/dashboard", "/history"]) {
      await page.goto(`${base}${path}`);
      await page.waitForURL(url => url.pathname === "/sign-in");
      assert.equal(new URL(page.url()).searchParams.get("redirect"), path);
    }
  });
} finally {
  await browser.close();
}
