// Global variable to store nutrition data
let nutritionGuide = {};

// Load nutrition data on page load
document.addEventListener('DOMContentLoaded', loadNutritionData);

// Load nutrition guide data
async function loadNutritionData() {
    try {
        const response = await fetch('data/nutrition_guide.json');
        nutritionGuide = await response.json();
        console.log('Nutrition guide loaded:', nutritionGuide);
        
        // Initialize with today's date if available
        const lastPeriodInput = document.getElementById('last-period-date');
        lastPeriodInput.addEventListener('change', calculatePregnancyWeek);
        
        // Set default date to today
        const today = new Date().toISOString().split('T')[0];
        lastPeriodInput.value = today;
        
        // Auto calculate
        calculatePregnancyWeek();
    } catch (error) {
        console.error('Error loading nutrition data:', error);
    }
}

// Calculate pregnancy week and day
function calculatePregnancyWeek() {
    const lastPeriodDate = document.getElementById('last-period-date').value;
    
    if (!lastPeriodDate) {
        document.getElementById('result').classList.add('hidden');
        return;
    }
    
    const lastPeriod = new Date(lastPeriodDate);
    const today = new Date();
    
    // Calculate difference in days
    const diffTime = today - lastPeriod;
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    // Calculate weeks and days
    const weeks = Math.floor(diffDays / 7);
    const days = diffDays % 7;
    
    // Determine pregnancy stage
    const stage = getPregnancyStage(weeks);
    
    // Display results
    document.getElementById('week').textContent = weeks;
    document.getElementById('day').textContent = days;
    document.getElementById('stage-name').textContent = stage.name;
    document.getElementById('stage-description').textContent = stage.description;
    
    // Update current info
    updateCurrentInfo(lastPeriodDate, weeks, days, stage);
    
    // Update nutrition details
    updateNutritionDetails(stage);
    
    // Update food tips
    updateFoodTips(stage);
    
    // Show result
    document.getElementById('result').classList.remove('hidden');
}

// Get pregnancy stage based on weeks
function getPregnancyStage(weeks) {
    const stages = nutritionGuide.pregnancy_stages;
    
    if (weeks <= 13) {
        return {
            key: 'early',
            ...stages.early
        };
    } else if (weeks <= 27) {
        return {
            key: 'middle',
            ...stages.middle
        };
    } else {
        return {
            key: 'late',
            ...stages.late
        };
    }
}

// Update current pregnancy information
function updateCurrentInfo(lastPeriodDate, weeks, days, stage) {
    // Format last period date
    const lastPeriod = new Date(lastPeriodDate);
    const formattedDate = lastPeriod.toLocaleDateString('ko-KR');
    
    document.getElementById('current-last-period').textContent = formattedDate;
    document.getElementById('current-week').textContent = `${weeks}주 ${days}일차`;
    document.getElementById('current-stage').textContent = stage.name;
    
    // Calculate due date (280 days from last period)
    const dueDate = new Date(lastPeriod);
    dueDate.setDate(dueDate.getDate() + 280);
    document.getElementById('due-date').textContent = dueDate.toLocaleDateString('ko-KR');
}

// Update nutrition details section
function updateNutritionDetails(stage) {
    const container = document.getElementById('nutrition-details');
    container.innerHTML = '';
    
    const requirements = stage.nutrition_requirements;
    const nutrients = stage.important_nutrients;
    
    // Create requirement cards
    const requirementHTML = `
        <div class="nutrition-card">
            <h4>📊 일일 권장량</h4>
            <p><strong>칼로리:</strong> ${requirements.calories}</p>
            <p><strong>단백질:</strong> ${requirements.protein}</p>
            <p><strong>엽산:</strong> ${requirements.folic_acid}</p>
            <p><strong>철분:</strong> ${requirements.iron}</p>
            <p><strong>칼슘:</strong> ${requirements.calcium}</p>
            <p><strong>DHA:</strong> ${requirements.dha}</p>
        </div>
    `;
    
    container.innerHTML += requirementHTML;
    
    // Create nutrient cards
    nutrients.forEach((nutrient, index) => {
        const nutrientHTML = `
            <div class="nutrition-card">
                <h4>🥬 ${nutrient.name}</h4>
                <p><strong>필요량:</strong> ${nutrient.amount}</p>
                <p><strong>효과:</strong> ${nutrient.benefit}</p>
                <p><strong>음식 출처:</strong></p>
                <ul>
                    ${nutrient.sources.map(source => `<li>${source}</li>`).join('')}
                </ul>
            </div>
        `;
        container.innerHTML += nutrientHTML;
    });
}

// Update food tips section
function updateFoodTips(stage) {
    const recommendedFoodsContainer = document.getElementById('recommended-foods');
    const cautionFoodsContainer = document.getElementById('caution-foods');
    
    // Clear previous content
    recommendedFoodsContainer.innerHTML = '';
    cautionFoodsContainer.innerHTML = '';
    
    // Add recommended foods
    stage.food_recommendations.forEach(food => {
        const li = document.createElement('li');
        li.textContent = food;
        recommendedFoodsContainer.appendChild(li);
    });
    
    // Add caution foods
    stage.food_cautions.forEach(food => {
        const li = document.createElement('li');
        li.textContent = food;
        cautionFoodsContainer.appendChild(li);
    });
}

// Initialize with default date
window.addEventListener('load', () => {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('last-period-date').value = today;
});
