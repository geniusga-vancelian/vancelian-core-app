-- Script pour annuler une transaction d'investissement
-- Usage: docker compose -f docker-compose.dev.yml exec postgres psql -U vancelian -d vancelian_core -f /path/to/cancel_investment.sql

-- 1. Trouver l'investissement ACCEPTED le plus récent
-- (Remplacez l'ID si vous voulez annuler un investissement spécifique)
DO $$
DECLARE
    v_transaction_id UUID;
    v_operation_id UUID;
    v_user_id UUID;
    v_offer_id UUID;
    v_amount NUMERIC;
    v_currency VARCHAR(3);
    v_offer_investment_id UUID;
BEGIN
    -- Trouver l'investissement ACCEPTED le plus récent (avec ou sans transaction)
    SELECT 
        COALESCE(op.transaction_id, NULL),
        oi.operation_id,
        oi.user_id,
        oi.offer_id,
        oi.accepted_amount,
        oi.currency,
        oi.id
    INTO v_transaction_id, v_operation_id, v_user_id, v_offer_id, v_amount, v_currency, v_offer_investment_id
    FROM offer_investments oi
    LEFT JOIN operations op ON oi.operation_id = op.id
    WHERE oi.status = 'ACCEPTED'
    ORDER BY oi.created_at DESC
    LIMIT 1;
    
    IF v_offer_investment_id IS NULL THEN
        RAISE EXCEPTION 'Aucun investissement ACCEPTED trouvé';
    END IF;
    
    IF v_operation_id IS NULL THEN
        RAISE EXCEPTION 'Aucune opération liée à cet investissement';
    END IF;
    
    RAISE NOTICE 'Transaction ID: %', v_transaction_id;
    RAISE NOTICE 'Operation ID: %', v_operation_id;
    RAISE NOTICE 'User ID: %', v_user_id;
    RAISE NOTICE 'Offer ID: %', v_offer_id;
    RAISE NOTICE 'Amount: % %', v_amount, v_currency;
    
    -- 2. Créer une opération REVERSAL pour déplacer les fonds de LOCKED vers AVAILABLE
    INSERT INTO operations (
        id,
        transaction_id,
        type,
        status,
        idempotency_key,
        operation_metadata,
        created_at,
        updated_at
    ) VALUES (
        gen_random_uuid(),
        v_transaction_id,
        'REVERSAL',
        'COMPLETED',
        NULL,
        jsonb_build_object(
            'currency', v_currency,
            'reason', 'Investment cancellation (manual)',
            'reversal_type', 'investment_cancellation',
            'original_operation_id', v_operation_id
        ),
        NOW(),
        NOW()
    )
    RETURNING id INTO v_operation_id;
    
    RAISE NOTICE 'Reversal Operation créée: %', v_operation_id;
    
    -- 3. Créer les ledger entries pour déplacer LOCKED -> AVAILABLE
    -- DEBIT WALLET_LOCKED (retirer des fonds verrouillés)
    INSERT INTO ledger_entries (
        id,
        operation_id,
        account_id,
        amount,
        currency,
        entry_type,
        created_at
    )
    SELECT
        gen_random_uuid(),
        v_operation_id,
        a.id,
        -v_amount,  -- Négatif pour DEBIT
        v_currency,
        'DEBIT',
        NOW()
    FROM accounts a
    WHERE a.user_id = v_user_id
      AND a.currency = v_currency
      AND a.account_type = 'WALLET_LOCKED'
    LIMIT 1;
    
    -- CREDIT WALLET_AVAILABLE (remettre les fonds disponibles)
    INSERT INTO ledger_entries (
        id,
        operation_id,
        account_id,
        amount,
        currency,
        entry_type,
        created_at
    )
    SELECT
        gen_random_uuid(),
        v_operation_id,
        a.id,
        v_amount,  -- Positif pour CREDIT
        v_currency,
        'CREDIT',
        NOW()
    FROM accounts a
    WHERE a.user_id = v_user_id
      AND a.currency = v_currency
      AND a.account_type = 'WALLET_AVAILABLE'
    LIMIT 1;
    
    -- 4. Mettre à jour le statut de la transaction à CANCELLED (si elle existe)
    IF v_transaction_id IS NOT NULL THEN
        UPDATE transactions
        SET status = 'CANCELLED',
            updated_at = NOW()
        WHERE id = v_transaction_id;
        RAISE NOTICE 'Transaction ID: % -> CANCELLED', v_transaction_id;
    ELSE
        RAISE NOTICE 'Aucune transaction liée (operation standalone)';
    END IF;
    
    -- 5. Mettre à jour le statut de l'investissement à REJECTED
    UPDATE offer_investments
    SET status = 'REJECTED',
        updated_at = NOW()
    WHERE id = v_offer_investment_id;
    
    -- 6. Décrémenter offer.committed_amount
    UPDATE offers
    SET committed_amount = GREATEST(0, committed_amount - v_amount),
        updated_at = NOW()
    WHERE id = v_offer_id;
    
    RAISE NOTICE 'Investissement annulé avec succès!';
    RAISE NOTICE 'Transaction ID: % -> CANCELLED', v_transaction_id;
    RAISE NOTICE 'Offer Investment ID: % -> REJECTED', v_offer_investment_id;
    RAISE NOTICE 'Fonds déplacés: % % de LOCKED vers AVAILABLE', v_amount, v_currency;
END $$;

