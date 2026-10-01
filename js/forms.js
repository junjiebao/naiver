/**
 * NAVIER YACHTS — Form submission handling
 *
 * Intercepts two forms and posts them to /api/enquiry, which forwards the
 * payload to a Lark group chat:
 *   1. Build enquiry form  (contact page)  -> data-enquiry-kind="enquiry"
 *   2. Newsletter signup   (footer)        -> data-enquiry-kind="subscribe"
 *
 * Uses event delegation on document so it also works on forms that are
 * injected after load (the footer is rendered by footer.js).
 *
 * If JavaScript is unavailable the forms still POST to /api/enquiry, so a
 * submission is never silently discarded.
 */

(function () {
  'use strict';

  var ENDPOINT = '/api/enquiry';
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

  var COPY = {
    sending: 'Sending\u2026',
    successEnquiry:
      'Thank you \u2014 your enquiry has been received. Our Dubai design team and Longkou engineering department will reply within one business day.',
    successSubscribe: 'Thank you \u2014 you are on the list. We will keep you posted on new builds.',
    genericError:
      'Something went wrong and your message could not be sent. Please email info@navieryacht.com or call +971 58 508 8518.',
    offline: 'You appear to be offline. Please check your connection and try again.',
    tooFast: 'Please wait a moment before submitting again.'
  };

  function isEnquiryForm(form) {
    return form.hasAttribute('data-enquiry-kind');
  }

  function kindOf(form) {
    return form.getAttribute('data-enquiry-kind') === 'subscribe' ? 'subscribe' : 'enquiry';
  }

  function fieldOf(form, name) {
    return form.querySelector('[name="' + name + '"]');
  }

  function valueOf(form, name) {
    var el = fieldOf(form, name);
    return el && typeof el.value === 'string' ? el.value.trim() : '';
  }

  function digitsOnly(value) {
    return String(value).replace(/\D/g, '');
  }

  /* ---------------------------------------------------------------- *
   * Status region
   * ---------------------------------------------------------------- */

  function statusRegion(form) {
    var existing = form.querySelector('.form-status');
    if (existing) return existing;

    var region = document.createElement('div');
    region.className = 'form-status';
    region.setAttribute('role', 'status');
    region.setAttribute('aria-live', 'polite');
    region.hidden = true;
    form.appendChild(region);
    return region;
  }

  function clearStatus(form) {
    var region = statusRegion(form);
    region.hidden = true;
    region.textContent = '';
    region.className = 'form-status';
  }

  function showStatus(form, state, message) {
    var region = statusRegion(form);
    region.hidden = false;
    region.className = 'form-status form-status--' + state;
    region.textContent = message;
  }

  /* ---------------------------------------------------------------- *
   * Field errors
   * ---------------------------------------------------------------- */

  function clearFieldErrors(form) {
    form.querySelectorAll('[aria-invalid="true"]').forEach(function (el) {
      el.removeAttribute('aria-invalid');
      var describedBy = el.getAttribute('aria-describedby');
      if (describedBy) {
        describedBy.split(/\s+/).forEach(function (id) {
          var node = document.getElementById(id);
          if (node && node.classList.contains('field-error')) node.remove();
        });
        el.removeAttribute('aria-describedby');
      }
    });
  }

  function markFieldError(form, name, message) {
    var el = fieldOf(form, name);
    if (!el) return;
    if (!el.id) el.id = 'field-' + name;
    var errorId = el.id + '-error';

    el.setAttribute('aria-invalid', 'true');

    var existing = document.getElementById(errorId);
    if (existing) return;

    var note = document.createElement('p');
    note.className = 'field-error';
    note.id = errorId;
    note.textContent = message;

    var group = el.closest('.form-group') || el.parentNode;
    group.appendChild(note);

    var describedBy = el.getAttribute('aria-describedby');
    el.setAttribute('aria-describedby', describedBy ? describedBy + ' ' + errorId : errorId);
  }

  /* ---------------------------------------------------------------- *
   * Validation (mirrors the server rules)
   * ---------------------------------------------------------------- */

  function validate(form) {
    var errors = [];
    var kind = kindOf(form);

    if (kind === 'subscribe') {
      if (!EMAIL_RE.test(valueOf(form, 'email'))) {
        errors.push(['email', 'Please enter a valid email address.']);
      }
      return errors;
    }

    if (valueOf(form, 'name').length < 2) {
      errors.push(['name', 'Please enter your name or company name.']);
    }
    if (digitsOnly(valueOf(form, 'phone')).length < 6) {
      errors.push(['phone', 'Please enter a reachable phone or WhatsApp number.']);
    }
    if (!EMAIL_RE.test(valueOf(form, 'email'))) {
      errors.push(['email', 'Please enter a valid email address.']);
    }
    if (valueOf(form, 'message').length < 5) {
      errors.push(['message', 'Please tell us a little about your project.']);
    }
    return errors;
  }

  /* ---------------------------------------------------------------- *
   * Submit button state
   * ---------------------------------------------------------------- */

  function setBusy(form, busy) {
    var buttons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
    buttons.forEach(function (btn) {
      if (busy) {
        btn.dataset.originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.setAttribute('aria-busy', 'true');
        if (btn.tagName === 'INPUT') {
          btn.dataset.originalValue = btn.value;
          btn.value = COPY.sending;
        } else {
          btn.innerHTML = COPY.sending;
        }
      } else {
        btn.disabled = false;
        btn.removeAttribute('aria-busy');
        if (btn.tagName === 'INPUT') {
          if (btn.dataset.originalValue) btn.value = btn.dataset.originalValue;
        } else if (btn.dataset.originalHtml) {
          btn.innerHTML = btn.dataset.originalHtml;
        }
      }
    });
  }

  /* ---------------------------------------------------------------- *
   * Payload
   * ---------------------------------------------------------------- */

  function buildPayload(form) {
    var payload = {
      kind: kindOf(form),
      page: window.location.pathname,
      website: valueOf(form, 'website')
    };

    form.querySelectorAll('input[name], textarea[name], select[name]').forEach(function (el) {
      if (el.name === 'website' || el.name === 'page') return;
      payload[el.name] = typeof el.value === 'string' ? el.value.trim() : el.value;
    });

    return payload;
  }

  /* ---------------------------------------------------------------- *
   * Submit handler
   * ---------------------------------------------------------------- */

  var submitting = false;

  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (!form || !isEnquiryForm(form)) return;

    event.preventDefault();

    if (submitting) return;

    clearStatus(form);
    clearFieldErrors(form);

    var errors = validate(form);
    if (errors.length) {
      errors.forEach(function (pair) {
        markFieldError(form, pair[0], pair[1]);
      });
      showStatus(form, 'error', errors.length === 1 ? errors[0][1] : 'Please correct the highlighted fields and try again.');
      var first = fieldOf(form, errors[0][0]);
      if (first) first.focus();
      return;
    }

    submitting = true;
    setBusy(form, true);
    showStatus(form, 'sending', COPY.sending);

    var payload = buildPayload(form);

    fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(payload)
    })
      .then(function (response) {
        return response
          .json()
          .catch(function () {
            return {};
          })
          .then(function (data) {
            return { ok: response.ok, status: response.status, data: data };
          });
      })
      .then(function (result) {
        if (result.ok && result.data && result.data.ok) {
          form.reset();
          showStatus(
            form,
            'success',
            kindOf(form) === 'subscribe' ? COPY.successSubscribe : COPY.successEnquiry
          );
          return;
        }

        var message = (result.data && result.data.error) || COPY.genericError;
        if (result.data && result.data.fallback) {
          message += ' ' + result.data.fallback;
        }
        if (Array.isArray(result.data && result.data.fields)) {
          result.data.fields.forEach(function (name) {
            markFieldError(form, name, 'Please check this field.');
          });
        }
        showStatus(form, 'error', message);
      })
      .catch(function () {
        showStatus(form, 'error', window.navigator.onLine === false ? COPY.offline : COPY.genericError);
      })
      .then(function () {
        submitting = false;
        setBusy(form, false);
      });
  });
})();
