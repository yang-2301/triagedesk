.PHONY: setup api web seed test eval clean

setup:
	cd backend && python3 -m pip install -r requirements.txt
	cd frontend && npm install

api:
	cd backend && PYTHONPATH=. python3 -m uvicorn app.main:app --port 8123 --reload

web:
	cd frontend && npm run dev

seed:
	cd backend && PYTHONPATH=. python3 ../scripts/seed.py

test:
	cd backend && PYTHONPATH=. python3 -m pytest -q

eval:
	cd backend && PYTHONPATH=. python3 -m app.ml.corpus && PYTHONPATH=. python3 - <<'EOF'
from app.ml.classifier import NaiveBayesClassifier
from app.ml import corpus
clf = NaiveBayesClassifier(alpha=0.3).fit(corpus.generate())
ev = corpus.generate_eval()
correct = sum(1 for l, t in ev if clf.predict(t)[0] == l)
print(f"triage accuracy on unseen wording: {correct}/{len(ev)} = {correct / len(ev):.2%}")
EOF

clean:
	rm -rf backend/data/*.db frontend/dist
