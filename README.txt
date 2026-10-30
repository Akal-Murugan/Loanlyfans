# LoanlyFans Frontend

## Install / update
1. Back up your existing `app.py`.
2. Copy this package's `app.py` into the same folder as your existing `backend.py`.
3. Copy the included `assets` folder into that same folder, so `assets/dog_mascot.png` and `assets/robot_mascot.png` are present.
4. Keep your existing `backend.py`, `loan_approval_pipeline.joblib`, `policy/` directory, and API secrets unchanged.
5. Run in your project terminal:

```powershell
streamlit run app.py
```

This is a frontend update and mascot asset pack. It calls your existing `process_loan_application()` function and does not retrain or replace your model.
